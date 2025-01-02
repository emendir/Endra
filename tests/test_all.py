from time import sleep

import _testing_utils
import test_endra
import test_multi_dev

_testing_utils.PYTEST = False

test_endra.run_tests()
test_multi_dev.run_tests()
sleep(1)
