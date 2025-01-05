from time import sleep

import _testing_utils
import test_endra

_testing_utils.PYTEST = False

test_endra.run_tests()
sleep(1)
