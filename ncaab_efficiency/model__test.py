import unittest
from . import model
#Test cases to test Calulator methods
#You always create  a child class derived from unittest.TestCase
class TestTempo(unittest.TestCase):
    
    def test_get_new_t(self):
        home_t, away_t = model.get_game_t(67.9, 70.2, 69.43, 69.06)
        self.assertAlmostEqual(home_t, 68.09, delta=.01)
        self.assertAlmostEqual(away_t, 70.39, delta=.01)
    
  
# Executing the tests in the above test case class
if __name__ == "__main__":
  unittest.main()