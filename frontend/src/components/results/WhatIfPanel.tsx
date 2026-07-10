import { ReactNode, useState, useMemo } from 'react';
import {
  Box, Typography, Card, CardContent, Stack, Button, Slider,
  CircularProgress, Alert, useTheme,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';
import { apiClient } from '../../services/api';
import type { WhatIfResponse } from '../../types';

const FACTOR_LABELS: Record<string, string> = {
  media_plan: 'Media Plan',
  promotions: 'Promotions',
  holidays: 'Holidays',
  weather: 'Weather',
  competitor: 'Competitor',
  economic: 'Economic',
  events: 'Events',
};

interface WhatIfPanelProps {
  forecastId: string;
  factorKeys: string[];
}

export function WhatIfPanel({ forecastId, factorKeys }: WhatIfPanelProps): ReactNode {
  const theme = useTheme();
  const [adjustments, setAdjustments] = useState<Record<string, number>>(
    Object.fromEntries(factorKeys.map((k) => [k, 1.0])),
  );
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasExternal = factorKeys.length > 0;

  const chartData = useMemo(() => {
    if (!result) return [];
    const map = new Map<string, { date: string; original: number | null; scenario: number | null }>();

    for (const fv of result.original_forecast) {
      map.set(fv.date, { date: fv.date, original: fv.forecast, scenario: null });
    }
    for (const fv of result.scenario_forecast) {
      const existing = map.get(fv.date);
      if (existing) {
        existing.scenario = fv.forecast;
      } else {
        map.set(fv.date, { date: fv.date, original: null, scenario: fv.forecast });
      }
    }
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [result]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, Record<string, number>> = {};
      for (const key of factorKeys) {
        const mult = adjustments[key];
        if (mult !== 1.0) {
          payload[key] = { media_spend_multiplier: mult, discount_multiplier: mult };
        }
      }
      const res = await apiClient.whatIf(forecastId, payload);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'What-if failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setAdjustments(Object.fromEntries(factorKeys.map((k) => [k, 1.0])));
    setResult(null);
    setError(null);
  };

  if (!hasExternal) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            No external factors used in this forecast. What-if analysis requires external factor data.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          What-if scenario analysis
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
          Adjust external factor multipliers to see how the forecast changes
        </Typography>

        <Stack spacing={2}>
          {factorKeys.map((key) => (
            <Box key={key}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {FACTOR_LABELS[key] ?? key}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {adjustments[key].toFixed(2)}×
                </Typography>
              </Stack>
              <Slider
                value={adjustments[key]}
                min={0}
                max={3}
                step={0.05}
                onChange={(_, v) => setAdjustments((prev) => ({ ...prev, [key]: v as number }))}
                sx={{ mx: 1, width: 'calc(100% - 16px)' }}
              />
            </Box>
          ))}

          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
              onClick={handleRun}
              disabled={loading}
              size="small"
            >
              {loading ? 'Running…' : 'Run scenario'}
            </Button>
            <Button
              variant="outlined"
              startIcon={<RestartAltIcon />}
              onClick={handleReset}
              disabled={loading}
              size="small"
            >
              Reset
            </Button>
          </Stack>

          {error && <Alert severity="error" sx={{ py: 0.5 }}>{error}</Alert>}

          {result && chartData.length > 0 && (
            <>
              <Box sx={{ width: '100%', height: 250 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend />
                    <ReferenceLine x={chartData[0]?.date} stroke={theme.palette.divider} />
                    <Line
                      type="monotone"
                      dataKey="original"
                      stroke={theme.palette.grey[400]}
                      dot={false}
                      strokeWidth={2}
                      strokeDasharray="6 3"
                      name="Original"
                    />
                    <Line
                      type="monotone"
                      dataKey="scenario"
                      stroke={theme.palette.primary.main}
                      dot={false}
                      strokeWidth={2.5}
                      name="Scenario"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </Box>

              <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap' }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Original forecast</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    ${result.original_forecast.reduce((s, f) => s + f.forecast, 0).toFixed(0)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Scenario forecast</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    ${result.scenario_forecast.reduce((s, f) => s + f.forecast, 0).toFixed(0)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Change</Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: (result.scenario_forecast.reduce((s, f) => s + f.forecast, 0) -
                        result.original_forecast.reduce((s, f) => s + f.forecast, 0)) >= 0
                        ? 'success.main' : 'error.main',
                    }}
                  >
                    {(result.scenario_forecast.reduce((s, f) => s + f.forecast, 0) -
                      result.original_forecast.reduce((s, f) => s + f.forecast, 0)) > 0 ? '+' : ''}
                    ${(result.scenario_forecast.reduce((s, f) => s + f.forecast, 0) -
                      result.original_forecast.reduce((s, f) => s + f.forecast, 0)).toFixed(0)}
                  </Typography>
                </Box>
              </Stack>
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
