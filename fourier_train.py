import pickle
import numpy as np
from numpy import fft
import pandas as pd
import warnings
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
import pylab as pl
import collections
import argparse

class FourierForecast:
        def __init__(self, train, test):
            self.train = np.array(train["values"])
            self.ds_train = np.array(train["timestamps"])
            self.test = np.array(test["values"])
            self.ds_test = np.array(test["timestamps"])

        def fourierExtrapolation(self, n_predict, n_harm):
                n = self.train.size             # number of harmonics in model                  
                t = np.arange(0, n)
                p = np.polyfit(t, self.train, 1)         # find linear trend in x
                train_notrend = self.train - p[0] * t        # detrended x
                train_freqdom = fft.fft(train_notrend)  # detrended x in frequency domain
                f = fft.fftfreq(n)              # frequencies
                indexes = np.arange(n).tolist()
                
                # sort indexes by frequency, lower -> higher
                indexes.sort(key = lambda i:np.absolute(f[i]))
         
                t = np.arange(0, n + n_predict)
                restored_sig = np.zeros(t.size)
                for i in indexes[:1 + n_harm * 2]:
                        ampli = np.absolute(train_freqdom[i]) / n   # amplitude
                        phase = np.angle(train_freqdom[i])          # phase
                        restored_sig += ampli * np.cos(2 * np.pi * f[i] * t + phase)
                return restored_sig + p[0] * t

        def fit_model(self, n_predict):
                
                minimum = np.min(self.train)
                stddev = np.std(self.train)

                upper = np.max(self.train) + stddev
                lower = minimum - stddev

                if minimum > 0:
                        lower = max(0, lower)

                # n_harm = 1/3 of number of data points was chosen by visual inspection
                n_harm = int(len(self.train)/3)
                forecast = self.fourierExtrapolation(n_predict, n_harm)

                ds = np.append(self.ds_train, self.ds_test)
                
                self.forecast = pd.DataFrame({"ds": ds, "yhat": forecast, "yhat_upper": upper,"yhat_lower": lower})

                return self.forecast

        def graph(self):
                pl.figure(figsize=(40,10))
                
                pl.plot(np.array(self.forecast["ds"]), np.array(self.forecast["yhat"]), 'y', label = 'yhat')
                pl.plot(self.ds_train, self.train, '*b', label = 'train', linewidth = 3)
                pl.plot(self.ds_test, self.test, '*g', label = 'test', linewidth = 3)
                pl.plot(np.array(self.forecast["ds"]), np.array(self.forecast["yhat_upper"]), 'y', label = 'yhat_upper')
                pl.plot(np.array(self.forecast["ds"]), np.array(self.forecast["yhat_lower"]), 'y', label = 'yhat_lower')
                
                pl.legend()
                pl.show()



def calc_delta(vals):
        diff = vals - np.roll(vals, 1)
        diff[0] = 0
        return diff

def monotonically_inc(vals):
        # check corner case
        if len(vals) == 1:
                return True
        diff = calc_delta(vals)
        diff[np.where(vals == 0)] = 0

        if ((diff < 0).sum() == 0):
                return True
        else:
                return False

if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="frun Prophet training on time series")

        parser.add_argument("--metric", type=str, help='metric name', required=True)

        parser.add_argument("--key", type=int, help='key number')
        
        args = parser.parse_args()

        metric_name = args.metric

        pkl_file = open("../pkl_data/" + metric_name + "_dataframes.pkl", "rb")
        dfs = pickle.load(pkl_file)
        pkl_file.close()
        key_vals = list(dfs.keys())

        selected = [args.key]
        for ind in selected:
                key = key_vals[ind]
                df = dfs[key]
                df = df.sort_values(by=['timestamps'])

                print(key)
                df["values"] = df["values"].apply(pd.to_numeric)
                vals = np.array(df["values"].tolist())

                # check if metric is a counter, if so, run AD on difference
                if monotonically_inc(vals):
                        print("monotonically_inc")
                        vals = calc_delta(vals)
                        df["values"] = vals
                
                train = df[0:int(0.7*len(vals))]
                test = df[int(0.7*len(vals)):]

                ff = FourierForecast(train, test)
                forecast = ff.fit_model(test.shape[0])
                
                f = open("../fourier_forecasts/forecast_" + metric_name + "_" + str(args.key) + ".pkl", "wb")
                pickle.dump(forecast, f)
                pickle.dump(train, f)
                pickle.dump(test,f)
                f.close()

                ff.graph()
