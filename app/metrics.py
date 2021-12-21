import numpy as np
import statistics
from datetime import datetime
from numpy.lib.function_base import median
from sklearn.linear_model import LinearRegression


def get_growth_rate(x, values_in_range, num_of_years, log_scale):
    """
    """

    # only compute the growth rate if the number of values is 
    # sufficient;
    # return None otherwise
    if len(values_in_range) == (num_of_years + 1):

        # run the model on the log scale if specified
        if log_scale:

            # run the model when all values within the given timewindow 
            # are positive
            if all(values_in_range > 0):
                y = np.log(values_in_range)

                # run linear regression on the log scale
                model = LinearRegression().fit(x, y)

                # return the growth rate based on the log scale linear 
                # model
                return np.exp(model.coef_)[0] - 1

            # return the growth rate based on the total growth 
            # directly, if there are non-positive values
            elif values_in_range[-1] > 0 and \
                values_in_range[-(num_of_years + 1)] > 0:

                # calculate the total growth for the given time window
                total_growth = \
                    values_in_range[-1] / values_in_range[-(num_of_years + 1)]
                return total_growth**(1 / num_of_years) - 1

            # return None otherwise
            else:
                return None
        
        # run the model on the linear scale
        else:
            y = values_in_range
            model = LinearRegression().fit(x, y)

            # return the model coefficiently directly 
            return model.coef_[0]

    # return None if the number of values is not sufficient
    else:
        return None


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

    def growth_rate(self, num_of_years=3, log_scale=True):
        """
        This method calculates the latest annual growth rate 'G' of the metric, 
        given a specific number of years. 

        For example, if asked to calculate the 3-year growth rate, 3 + 1 = 4 
        years of the most recent metric values will be used (to get 3 
        non-trivial intervals of annual growth). The growth rate 'G' will be 
        based on the coefficient 'A' of a linear regression fit of:
            'x': # years since year 0 for year n
            'y': log(the metri value for year n),

        where G = exp(A) - 1.
        """

        # prep x for the input data
        x = np.array(range(num_of_years + 1)).reshape((-1, 1))

        # get all values within range
        values_in_range = np.array(self.values[-(num_of_years + 1):])

        # get the growth rate
        rate = get_growth_rate(x=x, values_in_range=values_in_range, 
                               num_of_years=num_of_years, log_scale=log_scale)

        return rate

    def get_valid_values(self, num_of_years=10, disregarded_values=[0, np.nan]):
        """
        This method returns a list of 'valid' values within the given time 
        window.

        Inputs:
            'num_of_years': an integer object defaulted to 10.
            'disregarded_values': a list object defaulted to [0, np.nan]. 
                                  Values that fall into this list will NOT be 
                                  considered 'valid'.
        """

        # calculate the start date of the time window to be considered
        latest_reported_year = self.timestamps[-1].year
        start_date = datetime((latest_reported_year - num_of_years + 1), 1, 1)

        # get all metric values within the specified time window, except 
        # pre-specified values that need to be dropped
        values = np.array([self.data[timestamp] for timestamp in self.data 
                           if timestamp >= start_date and 
                              self.data[timestamp] not in disregarded_values])

        return values

    def percentile_rank(self, target_value, num_of_years=10, 
                        disregarded_values=[0, np.nan]):
        """
        This method calculates and returns the percentile rank of the target 
        value during the pre-specified time window. 
        """

        # get all metric values within the specified time window, except 
        # pre-specified values that need to be dropped
        values = self.get_valid_values(num_of_years=num_of_years, 
                                       disregarded_values=disregarded_values)
        
        # return the percentile rank of the target value, given the sequence of 
        # all qualified values.
        # return 50 if 'values' is empty
        rank = 100 * (target_value > values).sum() / len(values) \
            if len(values) > 0 else 50
        return rank 

    def pctrank_of_latest(self, latest='TTM', num_of_years=10):
        """
        This method calculates and returns the percentile rank of the 'latest' 
        value of the metric, within the pre-specified time window. 

        The returned value will be normalized to be between 0 and 1.

        Inputs:
            'latest': a string object defaulted to 'TTM'. 
            'num_of_years': an integer object defaulted to 10. 
        """

        if latest == 'TTM':
            latest_value = self.TTM_value
        else:
            latest_value = self.values[-1]
        
        return self.percentile_rank(
            target_value=latest_value, 
            num_of_years=num_of_years
            ) / 100, latest_value

    def get_range_info(self, latest='TTM', number_of_years=10, 
                       disregarded_values=[0, np.nan]):
        """
        This method derives the min, max, and median value of the metric within 
        the given time window, as well as the percentile rank of the given 
        latest value within the same time window.

        The derived values will be returned.

        Inputs:
            'latest': a string object defaulted to 'TTM'. 
            'num_of_years': an integer object defaulted to 10. 
        """

        # get valid values within range
        values = self.get_valid_values(num_of_years=number_of_years, 
                                       disregarded_values=disregarded_values)

        # get range statistics of all valid values
        if len(values) > 0:
            min_value, max_value = min(values), max(values)
            median_value = statistics.median(values)
        else:
            min_value, max_value, median_value = None, None, None

        # get the percentile rank for the 'latest' metric value
        pctrank_of_latest = self.pctrank_of_latest(latest=latest, 
                                                   num_of_years=number_of_years)

        return min_value, max_value, median_value, pctrank_of_latest

    def rating(self, benchmark_value=None, trend_interval=3, reverse=False, 
               latest='TTM', debug=False):
        """
        This helper function calculates the rating for the given metric, based 
        on a benchmark value if pre-specified, whether the metric has been 
        trending better or worse recently, etc.

        Inputs:
            'benchmark_value': a numeric value, defaulted to None. For example, 
                               it can be the industrial or S&P average/median 
                               value for the same metric.
            'trend_interval': a numeric value, defaulted to 3 (years). It's the 
                              time window used to calculate the trend of the 
                              metric values.
            'reverse': a boolean value, defaulted to False. If True, higher 
                       metric values indicate "better". 
            'latest': a string value, defaulted to 'TTM'. If 'TTM', the TTM 
                      value of the metric will be used to calculate the 
                      percentile rank. Otherwise, the latest value in the 
                      values sequence of the metric will be used.
        """

        # get the percentile rank based rating of the latest value, a value 
        # between 0 and 1
        percentile_rank_pct, latest_value = \
            self.pctrank_of_latest(latest=latest)
        rating_per_percentile_rank = \
            percentile_rank_pct if not reverse else (1 - percentile_rank_pct)

        # get the trend of recent values and the related rating, either 0 or 1
        trend_values = \
            self.growth_rate(num_of_years=trend_interval, log_scale=False) > 0
        if not trend_values and reverse:
            rating_per_trend_values = 1
        else:
            rating_per_trend_values = trend_values * (not reverse)

        # get the benchmark value based rating, a value between 0 and 1
        if benchmark_value:
            ratio_vs_benchmark = latest_value / benchmark_value
            if (ratio_vs_benchmark <= 1) and reverse:
                rating_per_benchmark_value = 1
            else:
                rating_per_benchmark_value = (ratio_vs_benchmark > 1) * \
                    (not reverse)
        else:
            rating_per_benchmark_value = 0

        # calculate and return the weighted average rating
        average_rating = ((1/3) * rating_per_percentile_rank + \
                          (1/3) * rating_per_trend_values + \
                          (1/3) * rating_per_benchmark_value) / \
                          ((2/3) + (1/3)*(benchmark_value is not None))

        if debug:
            return average_rating, rating_per_percentile_rank, \
                   rating_per_trend_values, rating_per_benchmark_value
        else:
            return average_rating


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
