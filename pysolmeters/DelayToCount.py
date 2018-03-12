"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""
# noinspection PyBroadException
from pysolmeters import max_int
from pysolmeters.AtomicInt import AtomicInt

# noinspection PyBroadException,PyPep8
try:
    from collections import OrderedDict
except:
    # noinspection PyPep8Naming,PyPackageRequirements,PyUnresolvedReferences
    from ordereddict import OrderedDict
import logging
from multiprocessing import Lock

logger = logging.getLogger(__name__)


class DelayToCount(object):
    """
    A class that associate delay intervals to occurrence count.
    Low level class without any lock.
    [0-100ms  ] => x hits
    [100-200ms] => y hits
    [...-...  ] => z hits
    """

    def __init__(self, instance_name, ar_delay=None):
        """
        Init
        :param ar_delay: Delay array to handle in millis (must finish with max int value, value in increasing order)
        :type ar_delay: list,tuple,None
        :param instance_name: Instance name
        :type instance_name: bytes
        :return Nothing
        """

        # Default is required
        if not ar_delay:
            ar_delay = [0, 50, 100, 500, 1000, 2500, 5000, 10000, 30000, 60000, max_int]

        # Name
        self._instance_name = instance_name

        # Hash (ordered)
        self._sorted_dict = OrderedDict()

        # Validate max int at the end (otherwise we may not be able to process and store some values)
        if ar_delay[len(ar_delay) - 1] != max_int:
            raise Exception("max_int required in last ar_delay item")

        # Validate order and prepare the hash
        prev = None
        for ms in ar_delay:
            if not prev:
                prev = ms
            elif prev >= ms:
                raise Exception("Not increasing value, prev={0}, ms={1}".format(prev, ms))

            # Hash it
            self._sorted_dict[ms] = AtomicInt()

    def put(self, delay_ms, increment_value=1):
        """
        Put a value for specified delay.
        :param delay_ms: Delay in millis
        :type delay_ms: int
        :param increment_value: Value to increment
        :type increment_value: int
        :return Nothing
        """

        # Found the good one
        aif = self._sorted_dict[max_int]
        for ms, ai in self._sorted_dict.items():
            if ms <= delay_ms and ms != max_int:
                aif = ai
            else:
                break

        # Go
        aif.increment(increment_value)

    def log(self):
        """
        Write to logger
        """

        ar = list(self._sorted_dict.keys())
        for i in range(0, len(ar) - 1):
            ms1 = ar[i]
            ms2 = ar[i + 1]
            if ms2 == max_int:
                ms2 = "MAX"
            ai = self._sorted_dict[ms1]
            logger.info("%s [%s-%s], c=%s", self._instance_name, ms1, ms2, ai.get())

    def to_dict(self):
        """
        To dict
        :return OrderedDict
        :rtype: OrderedDict
        """

        d = OrderedDict()
        ar = self._sorted_dict.keys()
        for i in range(0, len(ar) - 1):
            ms1 = ar[i]
            ms2 = ar[i + 1]
            if ms2 == max_int:
                ms2 = "MAX"
            ai = self._sorted_dict[ms1]
            out_k = "{0}|{1}-{2}".format(self._instance_name, ms1, ms2)
            out_v = ai.get()
            d[out_k] = out_v
        return d


class DelayToCountSafe(DelayToCount):
    """
    A class that associate delay intervals to occurrence count.
    This class use lock on put.
    [0-100ms  ] => x hits
    [100-200ms] => y hits
    [...-...  ] => z hits
    """

    def __init__(self, instance_name, ar_delay=None):
        """
        Init
        :param ar_delay: Delay array to handle in millis (must finish with max int value, value in increasing order)
        :type ar_delay: list,tuple,None
        :param instance_name: Instance name
        :type instance_name: bytes
        :return Nothing
        """

        self._lock = Lock()
        with self._lock:
            DelayToCount.__init__(self, instance_name, ar_delay)

    def put(self, delay_ms, increment_value=1):
        """
        Put a value for specified delay.
        :param delay_ms: Delay in millis
        :type delay_ms: int
        :param increment_value: Value to increment
        :type increment_value: int
        :return Nothing
        """

        with self._lock:
            DelayToCount.put(self, delay_ms, increment_value)

    def log(self):
        """
        Write to logger
        """
        with self._lock:
            DelayToCount.log(self)

    def to_dict(self):
        """
        To dict
        :return OrderedDict
        :rtype: OrderedDict
        """
        with self._lock:
            DelayToCount.to_dict(self)
