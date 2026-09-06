"""Scientific transformation checks, including exact pre-simplification membership."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from build_nepal_terrain import terrarium, tile_xy, build_candidates
from shapely.geometry import Polygon


class TerrainBuilderTest(unittest.TestCase):
    def test_terrarium_decodes_fractional_metres_not_rgb_interpolation(self):
        self.assertEqual(float(terrarium([128, 0, 0])), 0)
        self.assertEqual(float(terrarium([132, 210, 128])), 1234.5)
        self.assertEqual(float(terrarium([127, 255, 192])), -.25)

    def test_web_mercator_tile_orientation(self):
        x,y=tile_xy(0,0)
        self.assertEqual(float(x),2048);self.assertEqual(float(y),2048)
        east,north=tile_xy(85,28)
        self.assertGreater(east,x);self.assertLess(north,y)

    def test_exact_overlap_excludes_holes_outside_and_uncertain_damage(self):
        event=Polygon([(0,0),(500,0),(500,500),(0,500)], holes=[[(200,200),(300,200),(300,300),(200,300)]])
        buildings=[{'id':label,'grade':grade,'exactXY':xy} for label,grade,xy in [
            ('inside','destroyed',[100,100]), ('edge','damaged',[0,100]),
            ('uncertain','possible',[100,100]), ('hole','destroyed',[250,250]),
            ('outside','damaged',[501,100]), ('second-cell','damaged',[400,400])]]
        candidates=build_candidates(buildings,event)
        self.assertEqual({b['id'] for group in candidates.values() for b in group},{'inside','edge','second-cell'})
        self.assertEqual(len(candidates),2)


if __name__=='__main__':
    unittest.main()
