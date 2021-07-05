import numpy as np
from scipy import optimize
from scipy.signal import savgol_filter
import json

def linear_func(x, k, b):
    return k * x + b

def exp_func(x, a, b, c):
    return a * np.exp(-b * x) + c

def estimate_pb(pressure, st_sel, et_sel):

    pressure_hat = savgol_filter(pressure, 7, 1) # smooth

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
    length_pred = 100

    X_pred = np.arange(st_pred, st_pred + length_pred)
    y_pred = linear_func(X_pred, *p)
    y_target = pressure_hat[st_pred: st_pred + length_pred]

    errs = abs(y_pred - y_target)

    mask = (errs >= 3 * err_mean) * (np.arange(st_pred, st_pred + length_pred) >= mid_fit)

    print(np.where(mask == True)[0])

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

    print(type(min(y_target)) )
    target_line = {
        'label': 'Pressure',
        'x': X_pred,
        'y': y_target,
    }

    json.dumps(target_line)
    print("111")


    fitted_line = {
        'label': 'Fitted line',
        'x': X_pred,
        'y': y_pred,
    }
    json.dumps(fitted_line)
    print("222")

    cross_line0 = {
        'label': 'Pr',
        'x': [min(X_pred), max(X_pred)],
        'y': [pr, pr],
    }

    json.dumps(cross_line0)
    print("333")

    cross_line1 = {
        'label': '',
        'x': [index, index],
        'y': [min(y_target), max(y_target)],
    }
    json.dumps(cross_line1)
    print("444")

    lines = {
        'target_line': target_line,
        'fitted_line': fitted_line,
        'cross_line0': cross_line0,
        'cross_line1': cross_line1,
    }

    res = {
        'value': pr,
        'lines': lines
    }



    print(index, pressure_hat[index])
    print(res)
    return res

def estimate_pr_tangent(pressure, st_sel, et_sel):
    print(len(pressure))
    pressure_hat = savgol_filter(pressure, 7, 1)  # smooth

    st_fit = st_sel
    # length = min(30, int((et_sel-st_sel) * 0.05))
    length = int((et_sel - st_sel) * 0.05)
    length = max(5, length)

    et_fit = st_sel + length
    mid_fit = int((et_fit - st_fit) / 2)

    print(st_fit, et_fit)
    X = np.arange(st_fit, et_fit)
    y = pressure_hat[st_fit: et_fit]
    print(len(X), len(y))
    p, e = optimize.curve_fit(linear_func, X, y)
    y_fit = linear_func(X, *p)

    err_mean = np.mean(abs(y_fit - y))  # average regression error

    # predict
    st_pred = st_fit
    length_pred = 100

    X_pred = np.arange(st_pred, st_pred + length_pred)
    y_pred = linear_func(X_pred, *p)
    y_target = pressure_hat[st_pred: st_pred + length_pred]

    errs = abs(y_pred - y_target)

    mask = (errs >= 3 * err_mean) * (np.arange(st_pred, st_pred + length_pred) >= mid_fit)

    print(np.where(mask == True)[0])

    indexs = np.where(mask == True)[0]
    if len(indexs) == 0:
        return None

    index = st_pred + indexs[0]
    index = int(index)

    pr = pressure_hat[index]

    X_pred = X_pred.tolist()
    y_target = y_target.tolist()
    y_pred = y_pred.tolist()
    target_line = {
        'label': 'Pressure',
        'x': X_pred,
        'y': y_target,
    }
    fitted_line = {
        'label': 'Fitted line',
        'x': X_pred,
        'y': y_pred,
    }
    cross_line0 = {
        'label': 'Pr',
        'x': [min(X_pred), max(X_pred)],
        'y': [pr, pr],
    }
    cross_line1 = {
        'label': '',
        'x': [index, index],
        'y': [min(y_target), max(y_target)],
    }

    lines = {
        'target_line': target_line,
        'fitted_line': fitted_line,
        'cross_line0': cross_line0,
        'cross_line1': cross_line1,
    }

    res = {
        'value': pr,
        'lines': lines,
    }

    return res

def estimate_pr_muskat(pressure, st_sel, et_sel):
    pressure_hat = savgol_filter(pressure, 7, 1)  # smooth


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
            print(st_search, et_search, perr)
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

    pr = y_pred[0]

    X_pred = X_pred.tolist()
    y_target = y_target.tolist()
    y_pred = y_pred.tolist()
    target_line = {
        'label': 'Pressure',
        'x': X_pred,
        'y': y_target,
    }
    fitted_line = {
        'label': 'Fitted line',
        'x': X_pred,
        'y': y_pred,
    }

    cross_line0 = {
        'label': 'Pr',
        'x': [X_pred[0]-2, X_pred[0]],
        'y': [pr, pr],
    }
    cross_line1 = {
        'label': '',
        'x': [X_pred[0], X_pred[0]],
        'y': [0, pr],
    }

    cross_line2 = {
        'label': 'start index',
        'x': [best_st, best_st],
        'y': [0, max(y_target)],
    }

    lines = {
        'target_line': target_line,
        'fitted_line': fitted_line,
        'cross_line0': cross_line0,
        'cross_line1': cross_line1,
        'cross_line2': cross_line2,
    }

    res = {
        'value': pr,
        'lines': lines,
    }

    return res
