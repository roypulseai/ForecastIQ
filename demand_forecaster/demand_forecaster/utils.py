
import pandas as pd
import numpy as np

def ensure_datetime(df, col="date"):
    df = df.copy()
    df[col] = pd.to_datetime(df[col])
    return df

def week_of_month(dt, week_start='MON'):
    """Return 1-based index of the week within a month.
    Weeks are anchored to week_start (MON/TUE/.../SUN). Default MON.
    """
    anchor = {'MON':'W-MON','TUE':'W-TUE','WED':'W-WED','THU':'W-THU','FRI':'W-FRI','SAT':'W-SAT','SUN':'W-SUN'}[week_start]
    s = pd.Timestamp(dt)
    first = s.replace(day=1)
    weeknum_first = first.to_period(anchor)
    weeknum_curr = s.to_period(anchor)
    return (weeknum_curr - weeknum_first).n + 1

def period_start(dt, freq, week_start='MON'):
    if freq == 'D':
        return pd.Timestamp(dt).normalize()
    if freq == 'W':
        s = pd.Timestamp(dt).normalize()
        weekday_map = {'MON':0,'TUE':1,'WED':2,'THU':3,'FRI':4,'SAT':5,'SUN':6}
        target = weekday_map[week_start]
        delta = (s.weekday() - target) % 7
        return s - pd.Timedelta(days=delta)
    if freq == 'M':
        s = pd.Timestamp(dt).normalize()
        return s.replace(day=1)
    raise ValueError("Unsupported freq")

def wma(values):
    values = np.array(values, dtype=float)
    n = len(values)
    if n == 0:
        return np.nan
    weights = np.arange(1, n+1, dtype=float)
    return np.average(values, weights=weights)

def median(values):
    values = np.array(values, dtype=float)
    if len(values) == 0:
        return np.nan
    return float(np.nanmedian(values))

def pct_change(a, b):
    if b is None or b == 0 or pd.isna(b):
        return np.nan
    return (a - b) / b

def explode_events(events_df, attributes=None, lag_days=0):
    """Expand events (start..end) into daily rows, optionally shift by lag_days.
    Keeps any provided attribute columns to scope events.
    Required: event_id, event_name, start_date, end_date
    """
    if events_df is None or len(events_df) == 0:
        return pd.DataFrame(columns=['date','event_id','event_name'] + (attributes or []))
    ev = events_df.copy()
    ev['start_date'] = pd.to_datetime(ev['start_date'])
    ev['end_date'] = pd.to_datetime(ev['end_date'])
    out = []
    for _, r in ev.iterrows():
        if pd.isna(r['start_date']) or pd.isna(r['end_date']):
            continue
        d = r['start_date']
        while d <= r['end_date']:
            row = {'date': d + pd.Timedelta(days=lag_days),
                   'event_id': r.get('event_id', None),
                   'event_name': r.get('event_name', None)}
            if attributes:
                for a in attributes:
                    if a in ev.columns:
                        row[a] = r.get(a, None)
            out.append(row)
            d += pd.Timedelta(days=1)
    return pd.DataFrame(out)

def safe_merge_events(sales_df, events_daily, attributes=None):
    if events_daily is None or len(events_daily) == 0:
        return sales_df.copy()
    on_cols = ['date']
    if attributes:
        on_cols += [a for a in attributes if a in events_daily.columns]
    return sales_df.merge(events_daily, on=on_cols, how='left')
