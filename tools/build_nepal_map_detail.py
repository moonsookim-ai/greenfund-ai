"""Register dated Sentinel RGB and OSM map context to the existing local terrain.

Dependencies: requests, numpy, rasterio, Pillow, shapely. No inferred roads or buildings.
The imagery is pre-flood; OSM is location context with no current access status.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np
import requests
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.transform import from_bounds
from rasterio.enums import Resampling
from PIL import Image
from shapely.geometry import LineString, Polygon, Point, box

ROOT=Path(__file__).resolve().parents[1]
TERRAIN=ROOT/'greenproof/web/nepal/data/terrain'
OUT=ROOT/'greenproof/web/nepal/data/map-detail'
CACHE=ROOT/'out/terrain/detail'
ITEM_ID='S2C_45RUM_20260812_0_L2A'
ITEM_URL=f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{ITEM_ID}'
QUERY='[out:json][timeout:35];(way["highway"](28.13,85.30,28.30,85.41);way["building"](28.13,85.30,28.30,85.41);node["place"](28.13,85.30,28.30,85.41););out geom;'
KOREAN={'Shyaphru':'샤프루','Shyaphru Bensi':'샤프루베시','Bahun Danda':'바훈단다','Brabal':'브라발',
        'Bhrajam':'브라잠','Khangjim':'캉짐','Pajung':'파중','Bhanjyang':'반장','Surka':'수르카',
        'Timure':'티무레','Rasuwa Gadhi':'라수와가디','Resuo':'레수오','Thulo Syābru':'툴로샤브루',
        'Goljung':'골중','Sano Bharkhu':'사노바르쿠','Dursagang':'두르사강','Dalgaun':'달가운',
        'Aamachhodingmo':'아마초딩모'}


def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    item_path=CACHE/'selected-item.json'
    if not item_path.exists():
        response=requests.get(ITEM_URL,timeout=45);response.raise_for_status();write(item_path,response.json())
    item=json.loads(item_path.read_text(encoding='utf-8'))
    assert item['id']==ITEM_ID
    osm_path=CACHE/'osm-detail.json'
    if not osm_path.exists():
        response=requests.post('https://overpass-api.de/api/interpreter',data={'data':QUERY},
            headers={'User-Agent':'GREEN-PROOF-Research/1.0 (+https://greenfund.ai.kr)'},timeout=60)
        response.raise_for_status();osm_path.write_bytes(response.content)
    return item,json.loads(osm_path.read_text(encoding='utf-8'))


def registered_image(scene,item):
    x0,y0,x1,y1=scene['extent'];lon,lat=scene['origin']
    sx=6378137*math.pi/180*math.cos(math.radians(lat));sy=6378137*math.pi/180
    bounds=[lon+x0/sx,lat+y0/sy,lon+x1/sx,lat+y1/sy]
    width=round((x1-x0)/10);height=round((y1-y0)/10)
    affine=from_bounds(*bounds,width,height)
    cache_key={'item':item['id'],'bounds':bounds,'width':width,'height':height}
    key_path=CACHE/f'{scene["id"]}-registration.json'
    cached=key_path.exists() and json.loads(key_path.read_text())==cache_key
    arrays={}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='30'):
        for band in ('visual','scl'):
            path=CACHE/f'{scene["id"]}-{band}.npy'
            if not cached or not path.exists():
                with rasterio.open(item['assets'][band]['href']) as src:
                    assert src.crs.to_epsg()==32645
                    with WarpedVRT(src,crs='EPSG:4326',transform=affine,width=width,height=height,
                                   resampling=Resampling.bilinear if band=='visual' else Resampling.nearest) as vrt:
                        np.save(path,vrt.read())
            arrays[band]=np.load(path)
    write(key_path,cache_key)
    rgb=np.moveaxis(arrays['visual'][:3],0,-1);scl=arrays['scl'][0]
    assert rgb.shape==(height,width,3) and scl.shape==(height,width)
    # Unknown/defective/cloud pixels are transparent. Never replace them with invented ground.
    masked=np.isin(scl,[0,1,8,9,10]);cloud=np.isin(scl,[8,9,10])
    alpha=np.where(masked,0,255).astype('uint8')
    target=OUT/f'{scene["id"]}-sentinel.webp'
    Image.fromarray(np.dstack([rgb,alpha])).save(target,quality=91,method=6)
    return {'url':target.name,'acquiredAt':item['properties']['datetime'],'period':'pre-flood',
            'sourcePixelSizeM':10,'cloudMaskPixelSizeM':20,'width':width,'height':height,
            'boundsWGS84':bounds,'transform':list(affine)[:6],'rowOrder':'north-to-south',
            'crs':'EPSG:4326','sourceCRS':'EPSG:32645','rgbResampling':'bilinear','maskResampling':'nearest',
            'cloudFraction':round(float(cloud.mean()),6),'maskedFraction':round(float(masked.mean()),6),
            'snowFraction':round(float((scl==11).mean()),6),'sourceItem':ITEM_URL,'sourceId':item['id'],
            'assets':{band:item['assets'][band]['href'] for band in ('visual','scl')},
            'registeredCropSha256':{band:digest(CACHE/f'{scene["id"]}-{band}.npy') for band in arrays},
            'sha256':digest(target),'attribution':'Contains modified Copernicus Sentinel data (2026), via Element 84 Earth Search.'}


def map_context(scene,osm):
    lon,lat=scene['origin'];sx=6378137*math.pi/180*math.cos(math.radians(lat));sy=6378137*math.pi/180
    def xy(lon2,lat2):return (lon2-lon)*sx,(lat2-lat)*sy
    def coords(line):return [[round(x,1),round(y,1)] for x,y in line.coords]
    region=box(*scene['extent']);roads=[];buildings=[];places=[];invalid=0
    for feature in osm['elements']:
        tags=feature.get('tags',{});fid=feature['id']
        if feature['type']=='node' and tags.get('place') in ('hamlet','village','suburb','town','locality'):
            name=tags.get('name:en',tags.get('name'))
            if not name:continue
            point=Point(xy(feature['lon'],feature['lat']))
            if region.covers(point):
                places.append({'osmId':fid,'name':name,'label':KOREAN.get(name,tags.get('name:ko',name)),
                               'xy':[round(point.x,1),round(point.y,1)],'kind':tags['place']})
        if feature['type']!='way' or 'geometry' not in feature:continue
        points=[xy(p['lon'],p['lat']) for p in feature['geometry']]
        if 'highway' in tags and len(points)>1:
            clipped=LineString(points).intersection(region)
            lines=[clipped] if clipped.geom_type=='LineString' else [p for p in getattr(clipped,'geoms',[]) if p.geom_type=='LineString']
            for line in lines:
                if line.is_empty:continue
                roads.append({'osmId':fid,'kind':tags['highway'],'name':tags.get('name:en',tags.get('name','')),
                              'bridge':tags.get('bridge','no')!='no','xy':coords(line.simplify(1))})
        if 'building' in tags and tags['building']!='no' and len(points)>=4 and points[0]==points[-1]:
            poly=Polygon(points)
            if not poly.is_valid:invalid+=1;continue
            clipped=poly.intersection(region)
            polygons=[clipped] if clipped.geom_type=='Polygon' else [p for p in getattr(clipped,'geoms',[]) if p.geom_type=='Polygon']
            for poly in polygons:
                if not poly.is_empty:
                    buildings.append({'osmId':fid,'rings':[coords(r) for r in [poly.exterior,*poly.interiors]]})
    return {'roads':roads,'footprints':buildings,'places':places,'invalidFootprintsExcluded':invalid,
            'asOf':osm['osm3s']['timestamp_osm_base'],'accessStatus':None,'buildingHeights':None,
            'license':'ODbL-1.0','licenseUrl':'https://opendatacommons.org/licenses/odbl/1-0/',
            'attribution':'© OpenStreetMap contributors','query':QUERY,'endpoint':'https://overpass-api.de/api/interpreter'}


def main():
    item,osm=sources()
    for name in ('syapru','timure'):
        scene=json.loads((TERRAIN/f'{name}.json').read_text(encoding='utf-8'))
        imagery=registered_image(scene,item);context=map_context(scene,osm)
        data={'id':name,'origin':scene['origin'],'extent':scene['extent'],'imagery':imagery,'osm':context,
              'terrainSceneSha256':digest(TERRAIN/f'{name}.json'),'osmSourceSha256':digest(CACHE/'osm-detail.json')}
        write(OUT/f'{name}.json',data)
        print(name, 'roads',len(context['roads']),'footprints',len(context['footprints']),'places',len(context['places']),
              'cloud',imagery['cloudFraction'],'imagery bytes',(OUT/imagery['url']).stat().st_size,flush=True)
    write(OUT/'manifest.json',{'preparedOn':'2026-09-06','sourcePixelSizeM':10,'imageDate':'2026-08-12',
          'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(OUT.iterdir()) if p.name!='manifest.json'}})


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
