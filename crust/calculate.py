import numpy as np
from scipy import optimize
from scipy.signal import savgol_filter
import json
from .utils import piecewise_linear_two, linear_func, exp_func, my_linear_regreesion

from sklearn.linear_model import HuberRegressor

from scipy.ndimage.filters import uniform_filter1d

def estimate_pb(pressure, st_sel, et_sel):

    try:
        pressure = pressure[st_sel:et_sel]
        pb_index = int(np.argmax(pressure))
        pb = float(pressure[pb_index])

        pb_index = pb_index + st_sel
        lines = [
            {
                "name": "maximum",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {"x": [pb_index], "y": [pb]},
            },
        ]

        res = {
            'value': pb,
            'lines': lines
        }

    except Exception as e:
        print(str(e))
        return None

    return res

def estimate_pr(pressure, st_sel, et_sel, samplingFreq=7):

    try:
        # if samplingFreq % 2 == 0:
        #    samplingFreq += 1

        # pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
        pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

        st_fit = st_sel
        et_fit = st_sel + max(5, int((et_sel - st_sel) * 0.4))
        mid_fit = int((et_fit - st_fit) / 2)

        #regression
        X = np.arange(st_fit, et_fit)
        y = pressure_hat[st_fit: et_fit]
        p, e = optimize.curve_fit(linear_func, X, y)
        y_fit = linear_func(X, *p)

        err_mean = np.mean(abs(y_fit - y)) #average regreesion error

        #predict
        st_pred = st_fit
        #length_pred = 100
        length_pred = int(et_sel - st_sel)

        X_pred = np.arange(st_pred, st_pred + length_pred)
        y_pred = linear_func(X_pred, *p)
        y_target = pressure_hat[st_pred: st_pred + length_pred]

        errs = abs(y_pred - y_target)

        mask = (errs >= 3 * err_mean) * (np.arange(st_pred, st_pred + length_pred) >= mid_fit)

        #print(np.where(mask == True)[0])

        indexs = np.where(mask == True)[0]
        if len(indexs) == 0:
            return None

        index = indexs[0]
        index = st_pred + index
        index = int(index)

        pr = pressure_hat[index]

        X_pred = X_pred.tolist()
        y_target = y_target.tolist()
        y_pred = y_pred.tolist()

        # print(type(min(y_target)) )
        # target_line = {
        #     'label': 'Pressure',
        #     'x': X_pred,
        #     'y': y_target,
        # }
        #
        # #json.dumps(target_line)
        #
        #
        # fitted_line = {
        #     'label': 'Fitted line',
        #     'x': X_pred,
        #     'y': y_pred,
        # }
        # #json.dumps(fitted_line)
        #
        # cross_line0 = {
        #     'label': 'Pr',
        #     'x': [min(X_pred), max(X_pred)],
        #     'y': [pr, pr],
        # }
        #
        # #json.dumps(cross_line0)
        #
        # cross_line1 = {
        #     'label': '',
        #     'x': [index, index],
        #     'y': [min(y_target), max(y_target)],
        # }
        # #json.dumps(cross_line1)
        #
        #
        # lines = {
        #     'target_line': target_line,
        #     'fitted_line': fitted_line,
        #     'cross_line0': cross_line0,
        #     'cross_line1': cross_line1,
        # }
        lines = [
            {
                "name": "Origin Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_pred, 'y': y_target},
            },
            {
                "name": "Fitted Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X_pred, "y": y_pred},
            },
            {
                "name": "Pr = " + str(round(pr, 4)),
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [min(X_pred), max(X_pred)], "y": [pr, pr]},
            },
            {
                "name": "Deviation",
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [index, index], "y": [min(y_target), max(y_target)]},
            },
        ]

        res = {
            'value': pr,
            'lines': lines
        }

    except Exception as e:
        print(str(e))
        return None

    #print(index, pressure_hat[index])
    #print(res)
    return res

def estimate_ps_tangent(pressure, st_sel, et_sel, samplingFreq=7):
    try:
        # if samplingFreq % 2 == 0:
        #    samplingFreq += 1

        # pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
        pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

        st_fit = st_sel
        # length = min(30, int((et_sel-st_sel) * 0.05))
        length = int((et_sel - st_sel) * 0.05)
        length = max(5, length)

        et_fit = st_sel + length
        mid_fit = int((et_fit - st_fit) / 2)

        #print(st_fit, et_fit)
        X = np.arange(st_fit, et_fit)
        y = pressure_hat[st_fit: et_fit]
        #(len(X), len(y))
        p, e = optimize.curve_fit(linear_func, X, y)
        y_fit = linear_func(X, *p)

        err_mean = np.mean(abs(y_fit - y))  # average regression error

        # predict
        st_pred = st_fit
        length_pred = int(et_sel - st_sel)

        X_pred = np.arange(st_pred, st_pred + length_pred)
        y_pred = linear_func(X_pred, *p)
        y_target = pressure_hat[st_pred: st_pred + length_pred]

        errs = abs(y_pred - y_target)

        mask = (errs >= 3 * err_mean) * (np.arange(st_pred, st_pred + length_pred) >= mid_fit)

        #print(np.where(mask == True)[0])

        indexs = np.where(mask == True)[0]
        if len(indexs) == 0:
            return None

        index = st_pred + indexs[0]
        index = int(index)

        ps = pressure_hat[index]
        ps_inx = np.argmin(abs(pressure_hat-ps))
        ps = pressure_hat[ps_inx]


        cut_idxs = np.where(y_pred < np.min(y_target) )
        if len(cut_idxs) > 0:
            cut_idx = cut_idxs[0][0]
        else:
            cut_idx = -1

        X_pred = X_pred.tolist()
        y_target = y_target.tolist()
        y_pred = y_pred.tolist()



        lines = [
            {
                "name": "Origin Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_pred, 'y': y_target},
            },
            {
                "name": "Fitted Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X_pred[:cut_idx], "y": y_pred[:cut_idx]},
            },

            {
                "name": "Ps = " + str(round(ps, 4)),
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [min(X_pred), max(X_pred)], "y": [ps, ps]},
            },
            {
                "name": "Deviation",
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [index, index], "y": [min(y_target), max(y_target)]},
            },
        ]

        res = {
            'value': ps,
            'lines': lines,
        }
    except Exception as e:
        print(str(e))
        return None

    return res

def estimate_ps_muskat(pressure, st_sel, et_sel, samplingFreq=7):

    try:
        # if samplingFreq % 2 == 0:
        #    samplingFreq += 1

        # pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
        pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

        #fitting

        length_search = int(0.7 * (et_sel - st_sel))
        best_popt = None
        min_fit_err = np.inf
        best_st = None
        for i in range(length_search):
            # for i in range(1):
            st_search = st_sel + i
            et_search = et_sel

            # X_search = np.arange(st_search, et_search)
            # X_search = np.arange(st_search, et_search)
            X_search = np.arange(et_search - st_search)
            y_search = pressure_hat[st_search: et_search]

            # X_search_exp = np.exp(X_search)
            # y_search_log = np.logs(y_search)

            try:
                popt, pcov = optimize.curve_fit(exp_func, X_search, y_search)
                # print(popt)
                perr = np.sum(np.sqrt(np.diag(pcov)))
                #print(st_search, et_search, perr)
                if (perr < min_fit_err):
                    min_fit_err = perr
                    best_popt = popt
                    best_st = st_search
                    # print(i, perr)
            except:
                print("skip")


        # pred

        X_pred = np.arange(st_sel, et_sel)
        y_target = pressure_hat[st_sel: et_sel]
        y_pred = exp_func(X_pred - best_st, *best_popt)

        ps = y_pred[0]
        #ps_inx = np.argmin(abs(pressure_hat-ps))
        #ps = pressure_hat[ps_inx]


        X_pred = X_pred.tolist()
        y_target = y_target.tolist()
        y_pred = y_pred.tolist()
        # target_line = {
        #     'label': 'Pressure',
        #     'x': X_pred,
        #     'y': y_target,
        # }
        # fitted_line = {
        #     'label': 'Fitted line',
        #     'x': X_pred,
        #     'y': y_pred,
        # }
        #
        # cross_line0 = {
        #     'label': 'Pr',
        #     'x': [X_pred[0]-2, X_pred[0]],
        #     'y': [ps, ps],
        # }
        # cross_line1 = {
        #     'label': '',
        #     'x': [X_pred[0], X_pred[0]],
        #     'y': [0, ps],
        # }
        #
        # cross_line2 = {
        #     'label': 'start index',
        #     'x': [best_st, best_st],
        #     'y': [0, max(y_target)],
        # }

        lines = [
            {
                "name": "Origin Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_pred, 'y': y_target},
            },
            {
                "name": "Fitted Pressure",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X_pred, "y": y_pred},
            },

            {
                "name": "Ps = " + str(round(ps,4)),
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [X_pred[0]-2, X_pred[0]], "y": [ps, ps]},
            },
            {
                "name": "cross1",
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": False,
                "dataPoints": {"x": [X_pred[0], X_pred[0]], "y": [0, max(y_target)]},
            },
            {
                "name": "start index",
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [best_st, best_st], "y": [0, ps]},
            },
        ]

        res = {
            'value': ps,
            'lines': lines,
        }

    except Exception as e:
        print(str(e))
        return None

    return res


def estimate_ps_dp_dt(pressure, st_sel, et_sel, samplingFreq=7):

    # if samplingFreq % 2 == 0:
    #    samplingFreq += 1

    # pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
    pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

    pressure_hat_sel = pressure_hat[st_sel: et_sel]
    dp_dt = pressure_hat_sel[1:] - pressure_hat_sel[:-1]
    dp_dt = -abs(dp_dt)

    X = pressure_hat_sel[1:]
    X_range = (np.max(X) - np.min(X))
    X_min = np.min(X)
    X_norm = (X - X_min) / X_range

    y_target = -dp_dt
    y_range = np.max(y_target) - np.min(y_target)
    y_min = np.min(y_target)
    y_norm = (y_target - y_min) / y_range

    popt, pcov = optimize.curve_fit(piecewise_linear_two, X_norm, y_norm,
                                    bounds=[[np.min(X_norm), -np.inf, 0, 0], [np.max(X_norm), np.inf, np.inf, np.inf]])

    y_pred = piecewise_linear_two(X_norm, *popt) * y_range + y_min

    x0 = popt[0]

    ps = float(x0 * X_range + X_min)
    ps_inx = np.argmin(abs(pressure_hat - ps))
    ps = pressure_hat[ps_inx]


    X = X.tolist()
    y_target = y_target.tolist()
    y_pred = y_pred.tolist()



    target_line = {
        'label': 'Pressure',
        'x': X,
        'y': y_target,
    }
    fitted_line = {
        'label': 'Fitted line',
        'x': X,
        'y': y_pred,
    }
    lines = {
        'target_line': target_line,
        'fitted_line': fitted_line,
    }

    cross_line0 = {
        'label': 'Ps',
        'x': [ps, ps],
        'y': [min(y_target), max(y_target)],
    }

    lines = {
        'target_line': target_line,
        'fitted_line': fitted_line,
        'cross_line0': cross_line0,
    }

    res = {
        'value': ps,
        'lines': lines,
    }

    return res

    #plt.plot(X, y_target, "o")
    #plt.plot(X, y_pred)



def estimate_ps_dp_dt_robust(pressure, st_sel, et_sel, samplingFreq=7, resolution = 50):
    try:
        #if samplingFreq % 2 == 0:
        #    samplingFreq += 1

        #pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
        pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

        pressure_hat_sel = pressure_hat[st_sel: et_sel]
        dp_dt = pressure_hat_sel[1:] - pressure_hat_sel[:-1]
        dp_dt = -abs(dp_dt)

        X = pressure_hat_sel[1:]
        X_range = (np.max(X) - np.min(X))
        X_min = np.min(X)
        X_norm = (X - X_min) / X_range

        y = -dp_dt
        y_range = np.max(y) - np.min(y)
        y_min = np.min(y)
        y_norm = (y - y_min) / y_range

        regressor1 = HuberRegressor(warm_start=True)
        regressor2 = HuberRegressor(warm_start=True)



        delta = 1. / resolution
        X_split = []
        for i in range(1, resolution):
            X_split.append(i * delta)


        best_res = {}
        min_fit_err = np.inf


        for x1_split in X_split:
            # for x1_split in [0.2]:
            index1 = np.where(X_norm <= x1_split)[0]
            index2 = np.where((X_norm > x1_split))[0]

            if len(index1) < 5 or len(index2) < 5:
                continue

            X1 = X_norm[index1].reshape(-1, 1)
            y1 = y_norm[index1]

            regressor1.fit(X1, y1)

            if (regressor1.coef_[0] < 0):
                continue

            y1_pred = regressor1.predict(X1)

            errs1 = (y1_pred - y1)  # [ regressor1.outliers_ ==False ]

            X2 = X_norm[index2].reshape(-1, 1)
            y2 = y_norm[index2]

            regressor2.fit(X2, y2)
            if (regressor2.coef_[0] < 0):
                continue

            y2_pred = regressor2.predict(X2)
            errs2 = (y2_pred - y2)  # [  regressor2.outliers_ ==False]

            if (regressor2.coef_[0] < regressor1.coef_[0]):
                continue

            errs = np.concatenate([errs1, errs2])
            fit_err = abs(errs).mean()

            temp_k1, temp_k2 = regressor1.coef_[0], regressor2.coef_[0]
            temp_b1, temp_b2 = regressor1.intercept_, regressor2.intercept_
            x_intersect = (temp_b2 - temp_b1) / (temp_k1 - temp_k2)

            if not (0 < x_intersect and x_intersect < 1):
                print("outside")
                continue

            if fit_err < min_fit_err:
                min_fit_err = fit_err
                best_res['errs'] = errs
                best_res['k'] = [regressor1.coef_[0], regressor2.coef_[0]]
                best_res['b'] = [regressor1.intercept_, regressor2.intercept_]

                best_res['X1'] = X1
                best_res['y1_pred'] = y1_pred
                best_res['X2'] = X2
                best_res['y2_pred'] = y2_pred
                best_res['outliers_X'] = np.concatenate([X1[regressor1.outliers_], X2[regressor2.outliers_]])
                best_res['outliers_y'] = np.concatenate([y1[regressor1.outliers_], y2[regressor2.outliers_]])

        # plt.plot(X, y, 'o', label="-dp/dt vs. P")


        k1, k2 = best_res['k']
        b1, b2 = best_res['b']
        x_intersect = (b2 - b1) / (k1 - k2)

        X1_plot = np.array([0, x_intersect])
        y1_plot = k1 * X1_plot + b1

        X2_plot = np.array([x_intersect, 1])
        y2_plot = k2 * X2_plot + b2

        X1_plot = X1_plot * X_range + X_min
        X2_plot = X2_plot * X_range + X_min
        y1_plot = y1_plot * y_range + y_min
        y2_plot = y2_plot * y_range + y_min

        outliers_X, outliers_y = best_res['outliers_X'].flatten(), best_res['outliers_y'].flatten()
        outliers_X = outliers_X * X_range + X_min
        outliers_y = outliers_y * y_range + y_min


        #plt.plot(outliers_X, outliers_y, 'x', label="outliers")

        #plt.plot(X1_plot, y1_plot, label="the second stage")
        #plt.plot(X2_plot, y2_plot, label="the first stage")


        ps = x_intersect * X_range + X_min
        ps_inx = np.argmin(abs(pressure_hat-ps))
        ps = pressure_hat[ps_inx]

        #plt.plot([X_r, X_r], [np.max(y), np.min(y)], label="Pressure=" + str(round(X_r, 4)))
        #plt.legend()
        lines = [
            {
                "name": "-dP/dt vs. P",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': X.tolist(), 'y':y.tolist()},
            },
            {
                "name": "outliers",
                "type": "scatter",
                "markerType": "cross",
                "showInLegend": True,
                "dataPoints": {"x": outliers_X.tolist(), "y": outliers_y.tolist()},
            },
            {
                "name": "the second stage",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X1_plot.tolist(), "y": y1_plot.tolist()},
            },
            {
                "name": "the first stage",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X2_plot.tolist(), "y": y2_plot.tolist()},
            },
            {
                "name": "Pressure = " + str(round(ps, 4)),
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [float(ps), float(ps)], "y": [float(np.max(y)), float(np.min(y))]},
            },
        ]

        res = {
            'value': ps,
            'lines': lines,
        }

    except Exception as e:
        print(str(e))
        return None

    return res





def estimate_ps_dt_dp(pressure, st_sel, et_sel, samplingFreq=7, resolution=40):
    if samplingFreq % 2 == 0:
        samplingFreq += 1
    pressure_hat = savgol_filter(pressure, samplingFreq, 1)  # smooth
    pressure_hat_sel = pressure_hat[st_sel: et_sel]
    dp_dt = pressure_hat_sel[1:] - pressure_hat_sel[:-1]
    dp_dt = -abs(dp_dt)

    mask = abs(dp_dt) > 1e-5

    dt_dp = 1 / (dp_dt - 1e-3)

    X = pressure_hat_sel[1:][mask][::-1]
    X_range = (np.max(X) - np.min(X))
    X_min = np.min(X)
    X_norm = (X - X_min) / X_range

    y = dt_dp[mask][::-1]
    y_range = np.max(y) - np.min(y)
    y_min = np.min(y)
    y_norm = (y - y_min) / y_range


    delta = 1. / resolution
    X_split = []
    for i in range(1, resolution):
        for j in range(i + 1, resolution):
            X_split.append([i * delta, j * delta])

    best_res = {}
    min_fit_err = np.inf

    for x1, x2 in X_split:

        index1 = np.where(X_norm <= x1)[0]
        index2 = np.where((X_norm >= x1) * (X_norm <= x2))[0]
        index3 = np.where((X_norm >= x2))[0]
        if len(index1) < 4 or len(index2) < 4 or len(index3) < 4:
            continue

        X1 = X_norm[index1]
        y1 = y_norm[index1]
        k1, b1 = my_linear_regreesion(X1, y1)
        if k1 < 0:
            continue

        y1_pred = k1 * X1 + b1
        errs1 = y1_pred - y1

        start_x2 = np.max(X1)
        start_y2 = k1 * start_x2 + b1
        X2 = X_norm[index2]
        y2 = y_norm[index2]
        k2, b2 = my_linear_regreesion(X2, y2, start_x2, start_y2)
        if k2 < 0:
            continue

        y2_pred = k2 * X2 + b2
        errs2 = y2_pred - y2

        start_x3 = np.max(X2)
        start_y3 = k2 * start_x3 + b2
        X3 = X_norm[index3]
        y3 = y_norm[index3]
        k3, b3 = my_linear_regreesion(X3, y3, start_x3, start_y3)
        if k3 < 0:
            continue

        y3_pred = k3 * X3 + b3
        errs3 = y3_pred - y3

        if k3 > k1 or k3 > k2:
            continue

        errs = np.concatenate([errs1, errs2, errs3])
        fit_err = abs(errs).mean()

        if fit_err < min_fit_err:
            min_fit_err = fit_err
            best_res['errs'] = errs
            best_res['k'] = [k1, k2, k3]
            best_res['b'] = [b1, b2, b3]

            best_res['X1'] = X1
            best_res['y1_pred'] = y1_pred
            best_res['X2'] = X2
            best_res['y2_pred'] = y2_pred
            best_res['X3'] = X3
            best_res['y3_pred'] = y3_pred
            # best_res['start_x2'] = start_x2
            # best_res['start_y2'] = start_y2
            best_res['start_x3'] = start_x3
            # best_res['start_y3'] = start_y3

            print(k1, k2, k3)

    X1 = best_res['X1'] * X_range + X_min
    X2 = best_res['X2'] * X_range + X_min
    X3 = best_res['X3'] * X_range + X_min

    y1_pred = best_res['y1_pred'] * y_range + y_min
    y2_pred = best_res['y2_pred'] * y_range + y_min
    y3_pred = best_res['y3_pred'] * y_range + y_min
    #plt.plot(X1, y1_pred, )
    #plt.plot(X2, y2_pred, )
    #plt.plot(X3, y3_pred, )

    X = X.tolist()
    y = y.tolist()

    y1_pred = y1_pred.tolist()
    y2_pred = y2_pred.tolist()
    y3_pred = y3_pred.tolist()

    target_line = {
        'label': 'Pressure',
        'x': X,
        'y': y,
    }
    fitted_line0 = {
        'label': 'Fitted line (Stage 1)',
        'x': X,
        'y': y1_pred,
    }

    fitted_line1 = {
        'label': 'Fitted line (Stage 2)',
        'x': X,
        'y': y2_pred,
    }
    fitted_line2 = {
        'label': 'Fitted line (Stage 3)',
        'x': X,
        'y': y3_pred,
    }

    ps = float(best_res['start_x3'] * X_range + X_min)
    ps_inx = np.argmin(abs(pressure_hat - ps))
    ps = pressure_hat[ps_inx]

    cross_line0 = {
        'label': 'Ps',
        'x': [ps, ps],
        'y': [min(y), max(y)],
    }

    lines = {
        'target_line':  target_line,
        'fitted_line0': fitted_line0,
        'fitted_line1': fitted_line1,
        'fitted_line2': fitted_line2,
        'cross_line0':  cross_line0,
    }

    res = {
        'value': ps,
        'lines': lines,
    }

    return res


def estimate_ps_dt_dp_robust(pressure, st_sel, et_sel, samplingFreq=20, resolution=20):
    try:
        #if samplingFreq % 2 == 0:
        #    samplingFreq += 1
        #pressure_hat = savgol_filter(pressure, 7, 1)  # smooth
        pressure_hat = uniform_filter1d(pressure, size=samplingFreq)

        pressure_hat_sel = pressure_hat[st_sel: et_sel]
        dp_dt = pressure_hat_sel[1:] - pressure_hat_sel[:-1]
        dp_dt = -abs(dp_dt)

        mask = abs(dp_dt) > 4e-3

        dt_dp = 1 / (dp_dt - 1e-3)

        X = pressure_hat_sel[1:][mask][::-1]
        X_range = (np.max(X) - np.min(X))
        X_min = np.min(X)
        X_norm = (X - X_min) / X_range

        y = dt_dp[mask][::-1]
        y_range = np.max(y) - np.min(y)
        y_min = np.min(y)
        y_norm = (y - y_min) / y_range

        #print(X_range, X_min, y_range, y_min, )
        #print(X_norm, y_norm)

        regressor1 = HuberRegressor(warm_start=True)
        regressor2 = HuberRegressor(warm_start=True)
        regressor3 = HuberRegressor(warm_start=True)

        delta = 1. / resolution
        X_split = []
        for i in range(1, resolution):
            for j in range(i + 1, resolution):
                X_split.append([i * delta, j * delta])

        best_res = {}
        min_fit_err = np.inf


        for x1_split, x2_split in X_split:

            index1 = np.where(X_norm < x1_split)[0]
            index2 = np.where((X_norm >= x1_split) * (X_norm < x2_split))[0]
            index3 = np.where((X_norm >= x2_split))[0]
            
            assert len(index1) + len(index2) + len(index3) == len(X)

            if len(index1) < 4 or len(index2) < 4 or len(index3) < 4:
                continue

            X1 = X_norm[index1].reshape(-1, 1)
            y1 = y_norm[index1]
            regressor1.fit(X1, y1)
            if (regressor1.coef_[0] < 0):
                continue
            y1_pred = regressor1.predict(X1)
            errs1 = (y1_pred - y1)  # [ regressor1.outliers_ ==False ]

            X2 = X_norm[index2].reshape(-1, 1)
            y2 = y_norm[index2]
            regressor2.fit(X2, y2)
            if (regressor2.coef_[0] < 0):
                continue
            y2_pred = regressor2.predict(X2)
            errs2 = y2_pred - y2

            X3 = X_norm[index3].reshape(-1, 1)
            y3 = y_norm[index3]
            regressor3.fit(X3, y3)
            if (regressor3.coef_[0] < 0):
                continue
            #if (regressor3.coef_[0] > regressor1.coef_[0] or regressor3.coef_[0] > regressor2.coef_[0]):
            #    continue
            if not (regressor3.coef_[0] < regressor2.coef_[0] and regressor2.coef_[0] < regressor1.coef_[0]):
                continue

            y3_pred = regressor3.predict(X3)
            errs3 = y3_pred - y3


            errs = np.concatenate([errs1, errs2, errs3])
            fit_err = abs(errs).mean()

            temp_k1, temp_k2, temp_k3 = regressor1.coef_[0], regressor2.coef_[0], regressor3.coef_[0]
            temp_b1, temp_b2, temp_b3 = regressor1.intercept_, regressor2.intercept_, regressor3.intercept_
            x_intersect1 = (temp_b2 - temp_b1) / (temp_k1 - temp_k2)

            x_intersect2 = (temp_b3 - temp_b2) / (temp_k2 - temp_k3)

            if not (0 < x_intersect1 and x_intersect1 < x_intersect2 and x_intersect2 < 1):
                print("outside")
                continue

            if fit_err < min_fit_err:
                #print(x1_split, x2_split)
                min_fit_err = fit_err

                best_res['errs'] = errs
                best_res['k'] = [regressor1.coef_[0], regressor2.coef_[0], regressor3.coef_[0]]
                best_res['b'] = [regressor1.intercept_, regressor2.intercept_, regressor3.intercept_]

                best_res['X1'] = X1
                best_res['y1_pred'] = y1_pred
                best_res['X2'] = X2
                best_res['y2_pred'] = y2_pred
                best_res['X3'] = X3
                best_res['y3_pred'] = y3_pred

                best_res['outliers_X'] = np.concatenate(
                    [X1[regressor1.outliers_], X2[regressor2.outliers_], X3[regressor3.outliers_]])
                best_res['outliers_y'] = np.concatenate(
                    [y1[regressor1.outliers_], y2[regressor2.outliers_], y3[regressor3.outliers_]])

        k1, k2, k3 = best_res['k']
        b1, b2, b3 = best_res['b']
        x_intersect1 = (b2 - b1) / (k1 - k2)
        x_intersect2 = (b3 - b2) / (k2 - k3)
        X1_plot = np.array([0, x_intersect1])
        y1_plot = k1 * X1_plot + b1

        X2_plot = np.array([x_intersect1, x_intersect2])
        y2_plot = k2 * X2_plot + b2

        X3_plot = np.array([x_intersect2, 1])
        y3_plot = k3 * X3_plot + b3

        X1_plot = X1_plot * X_range + X_min
        X2_plot = X2_plot * X_range + X_min
        X3_plot = X3_plot * X_range + X_min

        y1_plot = y1_plot * y_range + y_min
        y2_plot = y2_plot * y_range + y_min
        y3_plot = y3_plot * y_range + y_min

        outliers_X, outliers_y = best_res['outliers_X'].flatten(), best_res['outliers_y'].flatten()
        #plt.plot(X, y, 'o', label="-dt/dp vs. P")

        outliers_X = outliers_X * X_range + X_min
        outliers_y = outliers_y * y_range + y_min
        #plt.plot(outliers_X, outliers_y, 'x', label="outliers")

        #plt.plot(X1_plot, y1_plot, label="the thrid stage")
        #plt.plot(X2_plot, y2_plot, label="the second stage")
        #plt.plot(X3_plot, y3_plot, label="the first stage")

        ps = x_intersect2 * X_range + X_min
        ps_inx = np.argmin(abs(pressure_hat-ps))
        ps = pressure_hat[ps_inx]

        #plt.plot([X_p, X_p], [np.max(y), np.min(y)], label="Pressure=" + str(round(X_p, 4)))
        print(x_intersect1, x_intersect2)



        lines = [
            {
                "name": "dt/dp vs. P",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': X.tolist(), 'y': y.tolist()},
            },
            {
                "name": "outliers",
                "type": "scatter",
                "markerType": "cross",
                "showInLegend": True,
                "dataPoints": {"x": outliers_X.tolist(), "y": outliers_y.tolist()},
            },
            {
                "name": "the third stage",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X1_plot.tolist(), "y": y1_plot.tolist()},
            },
            {
                "name": "the second stage",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X2_plot.tolist(), "y": y2_plot.tolist()},
            },
            {
                "name": "the first stage",
                "type": "line",
                "showInLegend": True,
                "dataPoints": {"x": X3_plot.tolist(), "y": y3_plot.tolist()},
            },
            {
                "name": "Pressure = " + str(round(ps, 4)),
                "type": "line",
                "lineDashType": "dash",
                "showInLegend": True,
                "dataPoints": {"x": [float(ps), float(ps)], "y": [float(np.max(y)), float(np.min(y))]},
            },
        ]

        res = {
            'value': ps,
            'lines': lines,
        }

    except Exception as e:
        print(str(e))
        return None

    return res