from datetime import datetime
import numpy as np


class Metric(object):
    """
    This class implements metrics from financial reports.
    """

    def __init__(self, name, timestamps, values, start_date, 
                 convert_to_numeric=True):
        """
        Constructor.
        
        Input:
            - "name": name of the metric.
            - "timestamps": a list (or list-like) of strings in the format of 
                            "%Y-%m"
            - "values": a sequence of values (could be strings) of the metric,
                        with each value corresponding to the timestamp of the 
                        same position in the input sequence of timestamps
            - "start_date": only records after this date from the input data 
                            will be considered
            - "convert_to_numeric": default to be True; if True the method 
                                    will attempt to convert all input values 
                                    to float values
        """

        # raise an error if the length of input timestamps is different from 
        # that of the input values
        if len(timestamps) != len(values):
            raise ValueError("The lengths of input timestamps and values must" 
                             "be equal.")

        # if requested, ensure all values are converted to numeric values (float)
        if convert_to_numeric:
            _values = [float(value) for value in values]
        else:
            _values = values

        # save the input data as a dictionary of "<timestamp>: <value>";
        # save the input "value" corresponding to the timestamp "TTM" 
        # separately
        self.data = {}
        for i in range(len(timestamps)):
            if timestamps[i] != 'TTM':
                timestamp = datetime.strptime(timestamps[i], '%Y-%m')
                if timestamp > start_date:
                    self.data[timestamp] = _values[i]
            else:
                self.TTM_value = _values[i]

        # save other needed attributes
        self.name = name
        self.timestamps = tuple(self.data.keys())
        self.values = tuple(self.data.values())


class TotalMetric(Metric):
    """
    This class implements "total" metrics such as "total revenues", "total net 
    income", etc. from financial reports, derived from the parent class of 
    Metric.

    These metrics can have both "total" values and "per share" values.
    """

    @property
    def num_of_shares(self):
        """
        This method is a getter method for the attribute num_of_shares.
        """

        return self._num_of_shares

    @num_of_shares.setter
    def num_of_shares(self, num_of_shares):
        """
        This method is a setter method for the attribute per_share_data.

        Inputs:
            'num_of_shares': a sequence of numbers representing the historical 
                             values of "shares outstanding". Each value in the
                             sequence should be associated with the same point
                             in time as that of value in the same position 
                             from the sequence of "self.values".
        """

        # check the input sequence and raise errors if needed
        if len(num_of_shares) != len(self.values):
            raise ValueError("The lengths of the input 'num_of_shares' and "
                             "the object attribute 'values' must be equal.")

        self._num_of_shares = num_of_shares
        self.per_share_values = list(
            np.array(self.values) / np.array(self._num_of_shares))
        self.per_share_data = dict(zip(self.timestamps, self.per_share_values))
