import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collector import classify, normalize

class ClassificationTests(unittest.TestCase):
    def test_topic(self):
        self.assertEqual(classify({'title':'食品製造設備支援','target_area_search':'長野県','target_number_of_employees':'20名以下'})[0],'有力候補・要確認')
    def test_outside(self):
        self.assertEqual(classify({'title':'設備','target_area_search':'東京都'})[0],'対象地域外の可能性')
    def test_employment(self):
        self.assertEqual(classify({'title':'新規雇用設備支援','target_area_search':'全国'})[0],'雇用条件に注意')
    def test_normalize(self):
        self.assertEqual(normalize({'id':'abc','title':'IT設備'})['id'],'abc')

if __name__=='__main__': unittest.main()
