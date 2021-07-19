import requests
from bs4 import BeautifulSoup
import datetime
import time
import random
import pandas as pd
import numpy as np
from io import StringIO
import json
from functools import reduce

## 技術面策略

##### 價量指標 #####

# 1. (Public) 今天某類型價格為 N 天中最高 (price_type=開盤/最高/最低／收盤)
def today_price_is_max_check_df(df, price_type="收盤", days=3):
    return df.apply(_today_price_is_max_check_row, price_type=price_type, days=days, axis=1)

def _today_price_is_max_check_row(row, price_type, days) -> bool:
    try:
        last_n_days_data = row["daily_k"][-1:(-1-days):-1]
        last_n_days_price = [each[1][price_type] for each in last_n_days_data]
        return last_n_days_price[0] == max(last_n_days_price)
    except:
        return False


# 2. (Public) 今天成交量不能為 N 天中最低
def today_volume_is_not_min_check_df(df, days=3):
    return df.apply(_today_volume_is_not_min_check_row, days=days, axis=1)

def _today_volume_is_not_min_check_row(row, days) -> bool:
    try:
        last_n_days_data = row["volume"][-1:(-1-days):-1]
        last_n_days_volume = [each[1] for each in last_n_days_data]
        return last_n_days_volume[0] != min(last_n_days_volume)
    except:
        return False


# 3. (Public) 近 N 天成交量皆大於等於 X 「張」
def volume_greater_check_df(df, shares_threshold=500, days=1):
    return df.apply(_volume_greater_check_row, shares_threshold=shares_threshold, days=days, axis=1)

def _volume_greater_check_row(row, shares_threshold, days) -> bool:
    # 如果只找今天的成交量的話，直接從「成交股數」欄位抓資料，因為這個欄位的資料較準確
    if days == 1 and row["成交股數"]:
        return (row["成交股數"] / 1000) >= shares_threshold
    try:
        last_n_days_data = row["volume"][-1:(-1-days):-1]
        last_n_days_volume = [each[1] for each in last_n_days_data]
        return all(single_day_volume >= shares_threshold for single_day_volume in last_n_days_volume)
    except:
        return False


# 4. (Public) 今天某類型價格不是 N 天中最低 (price_type=開盤/最高/最低／收盤)
def today_price_is_not_min_check_df(df, price_type="收盤", days=3):
    return df.apply(_today_price_is_not_min_check_row, price_type=price_type, days=days, axis=1)

def _today_price_is_not_min_check_row(row, price_type, days) -> bool:
    try:
        last_n_days_data = row["daily_k"][-1:(-1-days):-1]
        last_n_days_price = [each[1][price_type] for each in last_n_days_data]
        return last_n_days_price[0] != min(last_n_days_price)
    except:
        return False

##### 技術指標 #####

# 5. (Public) 今天的 X 指標「大於」今天的 Y 指標 (ex. MA1 > MA5 or K9 > D9) 並持續至少 N 天
#  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
def technical_indicator_greater_one_day_check_df(df, indicator_1="收盤", indicator_2="mean5", days=1):
    return df.apply(_technical_indicator_greater_one_day_check_row, indicator_1=indicator_1, indicator_2=indicator_2, days=days, axis=1)

def _technical_indicator_greater_one_day_check_row(row, indicator_1, indicator_2, days) -> bool:
    try:
        if indicator_1 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-1-days):-1]]
        if indicator_2 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-1-days):-1]]
        return all(i_1 > i_2 for i_1, i_2 in zip(last_n_days_indicator_1, last_n_days_indicator_2))
    except:
        return False


# 6. (Public) 今天的 X 指標與今天的 Y 指標差距小於 Z (ex. |D9-K9| < 10) 並持續至少 N 天
#  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
def technical_indicator_difference_one_day_check_df(df, indicator_1="k9", indicator_2="d9", difference_threshold=10, days=1):
    return df.apply(_technical_indicator_difference_one_day_check_row, indicator_1=indicator_1, indicator_2=indicator_2, difference_threshold=difference_threshold, days=days, axis=1)

def _technical_indicator_difference_one_day_check_row(row, indicator_1, indicator_2, difference_threshold, days) -> bool:
    try:
        if indicator_1 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-1-days):-1]]
        if indicator_2 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-1-days):-1]]
        return all(abs(i_1 - i_2) < difference_threshold for i_1, i_2 in zip(last_n_days_indicator_1, last_n_days_indicator_2))
    except:
        return False


# 7. (Public) 今天的 X 指標「大於或小於」(k * 昨天的 Y 指標) (ex. K9 > K9 or OSC > OSC or 今收 < 1.08昨收) 並持續至少 N 天
#  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
def technical_indicator_greater_or_less_two_day_check_df(df, indicator_1="k9", indicator_2="k9", direction="more", threshold=1, days=1):
    return df.apply(_technical_indicator_greater_or_less_two_day_check_row, indicator_1=indicator_1, indicator_2=indicator_2, direction=direction, threshold=threshold, days=days, axis=1)

def _technical_indicator_greater_or_less_two_day_check_row(row, indicator_1, indicator_2, direction, threshold, days) -> bool:
    try:
        if indicator_1 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-2-days):-1]]
        else:
            last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-2-days):-1]]
        if indicator_2 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-2-days):-1]]
        else:
            last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-2-days):-1]]
        if direction == "more":
            return all(last_n_days_indicator_1[i] > (threshold * last_n_days_indicator_2[i+1]) for i in range(days))
        else:
            return all(last_n_days_indicator_1[i] < (threshold * last_n_days_indicator_2[i+1]) for i in range(days)) 
    except:
        return False


# # 8. (Public) (今天的 X 指標 - 今天的 Y 指標) 小於 (k * 昨天的 Z 指標) (ex. (今收-今開) < (0.08*昨收)) 並持續至少 N 天
# #  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
# def technical_indicator_difference_two_day_check_df(df, indicator_1="收盤", indicator_2="開盤", difference_threshold=0.08, indicator_3="收盤", days=1):
#     return df.apply(_technical_indicator_difference_two_day_check_row, indicator_1=indicator_1, indicator_2=indicator_2, difference_threshold=difference_threshold, indicator_3=indicator_3, days=days, axis=1)

# def _technical_indicator_difference_two_day_check_row(row, indicator_1, indicator_2, difference_threshold, indicator_3, days) -> bool:
#     try:
#         if indicator_1 in ['開盤', '收盤', '最高', '最低']:
#             last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-2-days):-1]]
#         else:
#             last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-2-days):-1]]
#         if indicator_2 in ['開盤', '收盤', '最高', '最低']:
#             last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-2-days):-1]]
#         else:
#             last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-2-days):-1]]
#         if indicator_3 in ['開盤', '收盤', '最高', '最低']:
#             last_n_days_indicator_3 = [each[1][indicator_3] for each in row["daily_k"][-1:(-2-days):-1]]
#         else:
#             last_n_days_indicator_3 = [each[1] for each in row[indicator_3][-1:(-2-days):-1]]
#         difference_ = [i_1 - i_2 for i_1, i_2 in zip(last_n_days_indicator_1, last_n_days_indicator_2)]
#         return all(difference_[i] < (difference_threshold * last_n_days_indicator_3[i+1]) for i in range(days))
#     except:
#         return False


# 9. (Public) 今天的 X-Y 指標「大於等於」昨天的 X-Y 指標 (ex. 今天(k9-d9) >= 昨天(k9-d9)) 並持續至少 N 天
#  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
def technical_indicator_difference_greater_two_day_check_df(df, indicator_1="k9", indicator_2="d9", days=1):
    return df.apply(_technical_indicator_difference_greater_two_day_check_row, indicator_1=indicator_1, indicator_2=indicator_2, days=days, axis=1)

def _technical_indicator_difference_greater_two_day_check_row(row, indicator_1, indicator_2, days) -> bool:
    try:
        if indicator_1 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-2-days):-1]]
        else:
            last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-2-days):-1]]
        if indicator_2 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-2-days):-1]]
        else:
            last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-2-days):-1]]
        difference_list = [(i_1 - i_2) for i_1, i_2 in zip(last_n_days_indicator_1, last_n_days_indicator_2)]
        return all(difference_list[i] >= difference_list[i+1] for i in range(len(difference_list)-1))
    except:
        return False


# 10. (Public) 某兩個指標的黃金交叉發生於 N 日內 (指標1在上方，指標2在下方) (ex. 指標1 = 'K9', 指標2 = 'D9')
#  (indicator = 'k9', 'd9', 'dif', 'macd', 'osc', 'mean5', 'mean10', 'mean20', 'mean60', 'volume', '開盤', '收盤', '最高', '最低')
def golden_cross_check_df(df, indicator_1="k9", indicator_2="d9", days=5):
    return df.apply(_golden_cross_check_row, indicator_1=indicator_1, indicator_2=indicator_2, days=days, axis=1)

def _golden_cross_check_row(row, indicator_1, indicator_2, days) -> bool:
    try:
        if indicator_1 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_1 = [each[1][indicator_1] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_1 = [each[1] for each in row[indicator_1][-1:(-1-days):-1]]
        if indicator_2 in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator_2 = [each[1][indicator_2] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator_2 = [each[1] for each in row[indicator_2][-1:(-1-days):-1]]
        # 黃金交叉表示今天的 i_1 > i_2，且前一段時間內有至少一天 i_1 < i_2
        chk_1 = last_n_days_indicator_1[0] > last_n_days_indicator_2[0]
        chk_2 = any(i_1 < i_2 for i_1, i_2 in zip(last_n_days_indicator_1, last_n_days_indicator_2))
        return (chk_1 and chk_2)
    except:
        return False


# 11. (Public) X 指標要小於或大於參數 k 並持續至少 N 天
def technical_indicator_constant_check_df(df, indicator="k9", direction="more", threshold=20, days=1):
    return df.apply(_technical_indicator_constant_check_row, indicator=indicator, direction=direction, threshold=threshold, days=days, axis=1)

def _technical_indicator_constant_check_row(row, indicator, direction, threshold, days):
    try:
        if indicator in ['開盤', '收盤', '最高', '最低']:
            last_n_days_indicator = [each[1][indicator] for each in row["daily_k"][-1:(-1-days):-1]]
        else:
            last_n_days_indicator = [each[1] for each in row[indicator][-1:(-1-days):-1]]
        if direction == "more":
            return all(idx > threshold for idx in last_n_days_indicator)
        else:
            return all(idx < threshold for idx in last_n_days_indicator)
    except:
        return False