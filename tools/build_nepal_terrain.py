"""Build source-backed, static terrain scenes. No incident / person predictions.

Dependencies: requests numpy Pillow shapely pyshp. Public inputs are cached in out/.
"""
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import math
import sys
import zipfile
from html import escape

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'out/terrain'
sys.path.insert(0, str(CACHE / 'python-deps'))
import numpy as np
import requests
import shapefile
from PIL import Image
from shapely.geometry import shape, Point, box, mapping
from shapely.ops import transform, unary_union

OUT = ROOT / 'greenproof/web/nepal/data/terrain'
OUT.mkdir(parents=True, exist_ok=True)
CATALOG = 'https://ihp-wins.unesco.org/en/dataset/damage-grading-syapru-besi-and-timure-rasuwa-district-nepal-27-august-2026'
DOWNLOAD = 'https://ihp-wins.unesco.org/dataset/6ae71288-ec4b-4cd0-ad02-9bdc7f43df5d/resource/{}/download/emsr927_aoi{}_gra_product_{}_v1.zip'
RESOURCES = {
    '01': {'event': ('84cd6198-8049-4700-b97c-db87b751d2b9', 'observedeventa'),
           'buildings': ('f04cb326-fc9d-463d-8b2b-193825b7d857', 'builtupp'),
           'aoi': ('8cacb136-232e-4404-b667-b604abbf9539', 'areaofinteresta')},
    '02': {'event': ('a0f894cc-2c93-4fbf-a476-499a9d04ade9', 'observedeventa'),
           'buildings': ('fcb03d1a-fd24-4080-b553-e27445c4b786', 'builtupp'),
           'aoi': ('8de608db-a417-40ac-8880-d5542bc7a359', 'areaofinteresta')},
}
AREA_NAMES = {'01': ('syapru', '샤프루베시', 'Syapru Besi', 'SB'), '02': ('timure', '티무레', 'Timure', 'TM')}
HEADERS = {'User-Agent': 'GREEN-PROOF-Research/1.0 (+https://greenfund.ai.kr)'}
GRADE = {'Destroyed': 'destroyed', 'Damaged': 'damaged', 'Possibly damaged': 'possible'}
Z = 12
EARTH = 6378137


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_source(aoi, kind):
    folder = CACHE / 'cems' / f'{aoi}-{kind}'
    resource, stem = RESOURCES[aoi][kind]
    url = DOWNLOAD.format(resource, aoi, stem)
    if not list(folder.glob('*.shp')):
        folder.mkdir(parents=True, exist_ok=True)
        res = requests.get(url, headers=HEADERS, timeout=60)
        res.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
            for name in archive.namelist():
                if Path(name).suffix.lower() in ('.shp', '.shx', '.prj', '.dbf', '.cpg'):
                    (folder / Path(name).name).write_bytes(archive.read(name))
    shp = next(folder.glob('*.shp'))
    assert 'GCS_WGS_1984' in shp.with_suffix('.prj').read_text(), 'Unexpected source CRS'
    reader = shapefile.Reader(str(shp))
    rows = [(r.record.as_dict(), shape(r.shape.__geo_interface__)) for r in reader.iterShapeRecords()]
    assert all(g.is_valid and not g.is_empty for _, g in rows), 'Invalid source geometry'
    provenance = {'url': url, 'crs': 'EPSG:4326', 'features': len(rows),
                  'sha256': {p.name: sha(p) for p in sorted(folder.glob('*')) if p.suffix in ('.shp', '.dbf', '.shx', '.prj')}}
    return rows, provenance


def terrarium(rgb):
    data = np.asarray(rgb, dtype=np.float64)
    return data[..., 0] * 256 + data[..., 1] + data[..., 2] / 256 - 32768


def tile_xy(lon, lat):
    return (lon + 180) / 360 * 2**Z, (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * 2**Z


def load_tile(key):
    x, y = key
    folder = CACHE / 'tiles'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{Z}-{x}-{y}.png'
    meta = path.with_suffix('.json')
    url = f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png'
    if not path.exists() or not meta.exists():
        res = requests.get(url, headers=HEADERS, timeout=60)
        res.raise_for_status()
        Image.open(io.BytesIO(res.content)).verify()
        path.write_bytes(res.content)
        write_json(meta, {'url': url, 'tileLastModified': res.headers.get('Last-Modified'),
                         'imagerySources': res.headers.get('x-amz-meta-x-imagery-sources')})
    info = json.loads(meta.read_text())
    info['sha256'] = sha(path)
    assert 'srtm/' in info.get('imagerySources', ''), 'Review attribution if DEM source changes'
    image = Image.open(path)
    if image.mode == 'RGBA':
        assert np.asarray(image)[..., 3].min() == 255, 'Missing elevation samples'
    decoded = terrarium(image.convert('RGB'))
    assert np.isfinite(decoded).all() and decoded.min() > 0, 'Void / unexpected local elevation'
    return key, decoded, info


def elevation_grid(origin, extent, cols=101, rows=137):
    lon0, lat0 = origin
    scale_x = EARTH * math.pi / 180 * math.cos(math.radians(lat0))
    scale_y = EARTH * math.pi / 180
    xs = np.linspace(extent[0], extent[2], cols)
    ys = np.linspace(extent[3], extent[1], rows)
    lon, lat = np.meshgrid(lon0 + xs / scale_x, lat0 + ys / scale_y)
    tx, ty = tile_xy(lon, lat)
    # RGB samples are at pixel centres. Interpolate decoded elevations, never RGB.
    px, py = tx * 256 - .5, ty * 256 - .5
    ix, iy = np.floor(px).astype(int), np.floor(py).astype(int)
    keys = sorted({(int(x // 256), int(y // 256)) for xx, yy in ((ix, iy), (ix + 1, iy + 1), (ix, iy + 1), (ix + 1, iy)) for x, y in zip(xx.ravel(), yy.ravel())})
    with ThreadPoolExecutor(max_workers=4) as pool:
        loaded = list(pool.map(load_tile, keys))
    tiles = {key: data for key, data, _ in loaded}

    def sample(xx, yy):
        return np.array([tiles[(int(x // 256), int(y // 256))][y % 256, x % 256] for x, y in zip(xx.ravel(), yy.ravel())]).reshape(rows, cols)

    fx, fy = px - ix, py - iy
    values = sample(ix, iy) * (1 - fx) * (1 - fy) + sample(ix + 1, iy) * fx * (1 - fy) + sample(ix, iy + 1) * (1 - fx) * fy + sample(ix + 1, iy + 1) * fx * fy
    assert 200 < values.min() < values.max() < 8000
    return np.rint(values).astype('<u2'), [info for _, _, info in loaded]


def polygons(geometry):
    if geometry.geom_type == 'Polygon':
        return [[[round(x, 1), round(y, 1)] for x, y in ring.coords] for ring in [geometry.exterior, *geometry.interiors]]
    raise ValueError(geometry.geom_type)


def poly_list(geometry):
    geoms = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
    return [polygons(g) for g in geoms if g.geom_type == 'Polygon']


def build_candidates(buildings, event):
    groups = defaultdict(list)
    for b in buildings:
        if b['grade'] in ('destroyed', 'damaged') and event.covers(Point(b['exactXY'])):
            x, y = b['exactXY']
            groups[(math.floor(x / 250), math.floor(y / 250))].append(b)
    return groups


def build_scene(aoi, osm):
    slug, ko, en, prefix = AREA_NAMES[aoi]
    records = {}; sources = {}
    for kind in RESOURCES[aoi]:
        records[kind], sources[kind] = get_source(aoi, kind)
    aoi_wgs = unary_union([g for _, g in records['aoi']])
    origin = [round(aoi_wgs.centroid.x, 7), round(aoi_wgs.centroid.y, 7)]
    sx = EARTH * math.pi / 180 * math.cos(math.radians(origin[1]))
    sy = EARTH * math.pi / 180

    def local(x, y, z=None):
        return (np.asarray(x) - origin[0]) * sx, (np.asarray(y) - origin[1]) * sy

    aoi_geometry = transform(local, aoi_wgs)
    for props, _ in records['event']:
        assert props['event_type'] == '6-Mass Movement'
        assert props['det_method'] == 'Photo-interpretation'
    event = unary_union([transform(local, g) for _, g in records['event']])
    buildings = []
    for i, (props, geom) in enumerate(records['buildings']):
        x, y = local(geom.x, geom.y)
        buildings.append({'id': f'{prefix}-B{i+1:04d}', 'xy': [round(float(x), 1), round(float(y), 1)],
                          'exactXY': [float(x), float(y)], 'grade': GRADE[props['damage_gra']]})
    assert len({tuple(b['exactXY']) for b in buildings}) == len(buildings), 'Duplicate building points'
    assert all(aoi_geometry.buffer(1).covers(Point(b['exactXY'])) for b in buildings), 'Building outside AOI'
    groups = build_candidates(buildings, event)
    candidates = []
    # IDs express a spatial reading order; never an urgency score.
    for i, ((cx, cy), members) in enumerate(sorted(groups.items(), key=lambda item: (-item[0][1], item[0][0]))):
        center = [(cx + .5) * 250, (cy + .5) * 250]
        candidates.append({'id': f'{prefix}-{i+1:02d}', 'bounds': [cx*250, cy*250, (cx+1)*250, (cy+1)*250],
                           'center': center, 'lonLat': [round(origin[0]+center[0]/sx, 5), round(origin[1]+center[1]/sy, 5)],
                           'buildingIds': [b['id'] for b in members], 'counts': dict(Counter(b['grade'] for b in members))})
    bounds = aoi_geometry.bounds
    extent = [math.floor(bounds[0]/100)*100-1000, math.floor(bounds[1]/100)*100-1000,
              math.ceil(bounds[2]/100)*100+1000, math.ceil(bounds[3]/100)*100+1000]
    dem, tiles = elevation_grid(origin, extent)
    dem.tofile(OUT / f'{slug}.u16')
    dem_meta = {'url': f'{slug}.u16', 'encoding': 'uint16-little-endian', 'unit': 'm', 'rowOrder': 'north-to-south',
                'columns': dem.shape[1], 'rows': dem.shape[0], 'minimum': int(dem.min()), 'maximum': int(dem.max()),
                'gridSpacingM': [round((extent[2]-extent[0])/(dem.shape[1]-1), 1), round((extent[3]-extent[1])/(dem.shape[0]-1), 1)],
                'nominalSourceQualityM': 90, 'acquisitionYear': 2000, 'sourceTiles': tiles}
    rivers = []
    for el in osm['elements']:
        if el['type'] != 'way' or el.get('tags', {}).get('waterway') != 'river':
            continue
        from shapely.geometry import LineString
        line = LineString([local(p['lon'], p['lat']) for p in el['geometry']]).intersection(box(*extent))
        if line.is_empty:
            continue
        parts = [line] if line.geom_type == 'LineString' else [g for g in line.geoms if g.geom_type == 'LineString']
        for part in parts:
            rivers.append({'osmId': el['id'], 'name': el.get('tags', {}).get('name:en', el.get('tags', {}).get('name', 'River')),
                           'xy': [[round(x, 1), round(y, 1)] for x, y in part.simplify(2).coords]})
    write_json(OUT / f'{slug}-rivers.json', {'license': 'ODbL-1.0', 'attribution': '© OpenStreetMap contributors',
                                          'sourceTimestamp': osm['osm3s']['timestamp_osm_base'], 'rivers': rivers})
    for b in buildings:
        del b['exactXY']
    scene = {'id': slug, 'name': ko, 'englishName': en, 'aoi': aoi, 'origin': origin, 'extent': extent,
             'coordinateSystem': 'local equirectangular metres, x=east/y=north, origin WGS84 lon/lat',
             'observedAt': '2026-08-27T05:05:00Z', 'fieldValidated': False, 'dem': dem_meta,
             'eventPolygons': poly_list(event.simplify(3, preserve_topology=True)), 'aoiPolygons': poly_list(aoi_geometry),
             'eventAreaHa': round(sum(p['area'] for p, _ in records['event']), 2),
             'buildings': buildings, 'buildingCounts': dict(Counter(b['grade'] for b in buildings)),
             'candidates': candidates, 'candidateCellSizeM': 250,
             'candidateRule': 'unsimplified event polygon covers Destroyed or Damaged building point; 250m spatial grid; no urgency rank',
             'riverUrl': f'{slug}-rivers.json', 'sources': sources}
    write_json(OUT / f'{slug}.json', scene)
    write_fallback(scene, rivers)
    print(f'{slug}: {len(buildings)} building points; {len(candidates)} cells; {sum(len(c["buildingIds"]) for c in candidates)} overlapping building points; DEM {dem.min()}–{dem.max()}m')
    return scene


def write_fallback(s, rivers):
    # Source-backed vector map. This fallback is explicitly a plan view, not fake 3D.
    x0, y0, x1, y1 = s['extent']; w, h = x1-x0, y1-y0
    def path(rings):
        return ' '.join('M'+' L'.join(f'{x-x0:.1f},{y1-y:.1f}' for x,y in ring)+' Z' for ring in rings)
    output = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{s["name"]} 토사 이동과 피해 건물 평면도"><rect width="{w}" height="{h}" fill="#e8eee4"/>']
    for polygon in s['eventPolygons']:
        output.append(f'<path d="{path(polygon)}" fill="#e8ac64" fill-rule="evenodd"/>')
    for river in rivers:
        output.append('<polyline points="'+' '.join(f'{x-x0:.1f},{y1-y:.1f}' for x,y in river['xy'])+'" fill="none" stroke="#217cad" stroke-width="18"/>')
    for polygon in s['aoiPolygons']:
        output.append(f'<path d="{path(polygon)}" fill="none" stroke="#536966" stroke-width="12" stroke-dasharray="35 25"/>')
    for c in s['candidates']:
        x,y,_,_=c['bounds']
        output.append(f'<rect x="{x-x0:.1f}" y="{y1-y-250:.1f}" width="250" height="250" fill="none" stroke="#663caf" stroke-width="10"/>')
    for b in s['buildings']:
        x,y=b['xy'];color='#ac302d' if b['grade']=='destroyed' else '#814c25'
        px,py=x-x0,y1-y
        if b['grade']=='destroyed':
            output.append(f'<rect x="{px-12:.1f}" y="{py-12:.1f}" width="24" height="24" fill="{color}"/>')
        elif b['grade']=='damaged':
            output.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="12" fill="{color}"/>')
        else:
            output.append(f'<path d="M{px:.1f},{py-14:.1f} l14,14 -14,14 -14,-14 Z" fill="none" stroke="#78453d" stroke-width="5"/>')
    output.append('</svg>')
    (OUT/f'{s["id"]}-plan.svg').write_text(''.join(output),encoding='utf-8')


def main():
    osm_path = CACHE / 'osm.json'
    if not osm_path.exists():
        query = '[out:json][timeout:35];way["waterway"="river"](28.13,85.30,28.30,85.40);out geom;'
        res = requests.post('https://overpass-api.de/api/interpreter', data={'data':query}, headers=HEADERS, timeout=60)
        res.raise_for_status(); osm_path.write_bytes(res.content)
    osm = json.loads(osm_path.read_text(encoding='utf-8'))
    scenes = [build_scene(aoi, osm) for aoi in AREA_NAMES]
    manifest = {'version':1, 'preparedOn':'2026-09-06', 'model':'GPT-6 Astra', 'observationDate':'2026-08-27',
                'purpose':'한국 구조대원의 지형·피해 대조를 위한 참고 모델',
                'burialDepth':None, 'burialProbability':None, 'liveFloodExtent':None, 'safeRoutes':None,
                'sourceCatalog':CATALOG, 'activation':'https://mapping.emergency.copernicus.eu/activations/EMSR927/',
                'attribution':'Contains modified Copernicus Emergency Management Service information (2026), EMSR927 AOI01/02 GRA v1. © European Union. SRTM data courtesy of the U.S. Geological Survey, via Mapzen Terrain Tiles. © OpenStreetMap contributors.',
                'osmSourceSha256':sha(osm_path), 'scenes':[{'id':s['id'],'name':s['name'],'url':s['id']+'.json', 'cells':len(s['candidates']), 'buildings':len(s['buildings'])} for s in scenes],
                'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.iterdir()) if p.name!='manifest.json'}}
    write_json(OUT/'manifest.json',manifest)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
