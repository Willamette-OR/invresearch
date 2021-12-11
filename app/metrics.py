import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression


class Metric(object):
    """
    This class implements metrics from financial reports.
    """

    def __init__(self, name, timestamps, values, start_date, 
                 input_timestamps_format='%Y-%m', convert_to_numeric=True,
                 str_defaulted_to=0):
        """
        Constructor.
        
        Input:
            - "name": name of the metric.
            - "timestamps": a list (or list-like) of strings in the format 
                            specified by the other input 
                            'input_timestamps_format'
            - "values": a sequence of values (could be strings) of the metric,
                        with each value corresponding to the timestamp of the 
                        same position in the input sequence of timestamps
            - "start_date": a Python datetime object - only records after this 
                            date from the input data will be considered 
            - "input_timestamps_format": default "%Y-%m". Format used to 
                                         convert string formatted input 
                                         timestamps to Python datetime objects.
            - "convert_to_numeric": default to be True; if True the method 
                                    will attempt to convert all input values 
                                    to float values
            - 'str_defaulted_to': the default value to default an input string 
                                  value to, when trying to convert values in 
                                  the input 'values' to numeric values.
        """

        # raise an error if the length of input timestamps is different from 
        # that of the input values
        if len(timestamps) != len(values):
            raise ValueError("The lengths of input timestamps and values must" 
                             "be equal.")

        # if requested, ensure all values are converted to numeric values 
        # (float)
        # TODO - occasionally a value could be None if the input values are 
        # from analyst estimates (Guru). Defaulting those values to 0 for now.
        if convert_to_numeric:
            _values = []
            for value in values:
                try:
                    _values.append(float(value))
                except:
                    _values.append(str_defaulted_to)
        else:
            _values = values

        # save the input data as a dictionary of "<timestamp>: <value>";
        # save the input "value" corresponding to the timestamp "TTM" 
        # separately
        self.data = {}
        for i in range(len(timestamps)):
            if timestamps[i] != 'TTM':
                timestamp = datetime.strptime(timestamps[i], 
                                              input_timestamps_format)
                if timestamp > start_date:
                    self.data[timestamp] = _values[i]
            else:
                self.TTM_value = _values[i]

        # save other needed attributes
        self.name = name
        self.timestamps = tuple(self.data.keys())
        self.values = tuple(self.data.values())

    def get_timestamps_str(self, timestamps_format='%Y-%m'):
        """
        This method returns the saved timestamps in the string format.
        """

        return [timestamp.strftime(timestamps_format) for timestamp in \
            self.timestamps]

    def __add__(self, other):
        """
        This special function overloads the add operator '+'.
        """

        if self.timestamps != other.timestamps:
            raise ValueError("Timestamp sequences of the two input metrics "
                             "must be identical.")
        else:
            name_sum = '{} + {}'.format(self.name, other.name)
            timestamps_sum = self.get_timestamps_str()
            values_sum = list(
                np.array(self.values) + np.array(other.values))
            summation = Metric(name=name_sum, 
                               timestamps=timestamps_sum,
                               values=values_sum,
                               start_date=datetime(1900, 1, 1))
            summation.TTM_value = self.TTM_value + other.TTM_value

            return summation

    def __truediv__(self, other):
        """
        This special function overloads the division operator '/'.
        """

        if self.timestamps != other.timestamps:
            raise ValueError("Timestamp sequences of the two input metrics "
                             "must be identical.")
        else:
            name_division = '{} / {}'.format(self.name, other.name)
            timestamps_division = self.get_timestamps_str()
            values_division = list(
                np.array(self.values) / np.array(other.values))
            division = Metric(name=name_division, 
                              timestamps=timestamps_division,
                              values=values_division,
                              start_date=datetime(1900, 1, 1))
            division.TTM_value = self.TTM_value / other.TTM_value
            
            return division

    def growth_rate(self, num_of_years=3):
        """
        This method calculates the latest annual growth rate 'G' of the metric, 
        given a specific number of years. 

        For example, if asked to calculate the 3-year growth rate, 3 + 1 = 4 
        years of the most recent metric values will be used (to get 3 
        non-trivial intervals of annual growth). The growth rate 'G' will be 
        based on the coefficient 'A' of a linear regression fit of:
            'x': # years since year 0 for year n
            'y': log(the metri value for year n),

        where G = 10^A - 1.
        """

        try:
            # prep input data, and y will be the natural logs of metric values
            x = np.array(range(num_of_years + 1)).reshape((-1, 1))
            y = np.log(self.values[-(num_of_years + 1):])

            # run linear regression on the log scale
            model = LinearRegression().fit(x, y)

            # get the growth rate based on the log scale linear model
            return np.exp(model.coef_)[0] - 1
        except:
            # if a log scale linear regression errors out, use a less ideal 
            # formula to compute the CAGR
            if len(self.values) < num_of_years + 1:
                return None
            else:
                total_growth = \
                    self.values[-1] / self.values[-(num_of_years + 1)]
                if total_growth > 0:
                    return total_growth**(1 / num_of_years) - 1
                else:
                    return None

    def percentile_rank(self, target_value, num_of_years=10, 
                        disregarded_values=[0, np.nan]):
        """
        This method calculates and returns the percentile rank of the target 
        value during the pre-specified time window. 
        """

        # calculate the start date of the time window to be considered
        latest_reported_year = self.timestamps[-1].year
        start_date = datetime((latest_reported_year - num_of_years + 1), 1, 1)

        # get all metric values within the specified time window, except 
        # pre-specified values that need to be dropped
        values = np.array([self.data[timestamp] for timestamp in self.data 
                           if timestamp > start_date and 
                              self.data[timestamp] not in disregarded_values])
        
        # return the percentile rank of the target value, given the sequence of 
        # all qualified values.
        return 100 * (target_value > values).sum() / len(values)


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
        if len(num_of_shares) == 1:

            # assuming the caller intends to use a constant value for all dates
            self._num_of_shares = num_of_shares * len(self.values)

        elif len(num_of_shares) != len(self.values):
            raise ValueError("The lengths of the input 'num_of_shares' and "
                             "the object attribute 'values' must be equal.")
        else:
            self._num_of_shares = num_of_shares

        self.per_share_values = list(
            np.array(self.values) / np.array(self._num_of_shares))
        self.per_share_data = dict(zip(self.timestamps, self.per_share_values))
