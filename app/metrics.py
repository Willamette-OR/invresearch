from datetime import datetime


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

