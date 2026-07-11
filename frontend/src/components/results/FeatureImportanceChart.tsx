import { ReactNode, useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, ZAxis } from 'recharts';
import { Box, Typography, Card, CardContent, FormControl, Select, MenuItem, Stack, useTheme } from '@mui/material';
import type { ForecastValue } from '../../types';

interface FeatureImportanceChartProps {
  featureImportance: Record<string, number> | null | undefined;
  modelName?: string;
  forecastValues?: ForecastValue[];
}

export function FeatureImportanceChart({ featureImportance, modelName, forecastValues }: FeatureImportanceChartProps): ReactNode {
  const theme = useTheme();
  const [view, setView] = useState<'importance' | 'shap'>('importance');

  // Per-step SHAP data (beeswarm-style)
  const shapData = useMemo(() => {
    if (!forecastValues) return null;
    const features = new Map<string, Array<{ step: number; value: number }>>();
    for (let i = 0; i < forecastValues.length; i++) {
      const fv = forecastValues[i];
      if (!fv.shap) continue;
      for (const [feat, val] of Object.entries(fv.shap)) {
        if (!features.has(feat)) features.set(feat, []);
        features.get(feat)!.push({ step: i, value: val });
      }
    }
    if (features.size === 0) return null;
    // Sort features by mean absolute SHAP value descending
    const sorted = Array.from(features.entries())
      .map(([feat, vals]) => ({
        feat,
        vals,
        meanAbs: vals.reduce((s, v) => s + Math.abs(v.value), 0) / vals.length,
      }))
      .sort((a, b) => b.meanAbs - a.meanAbs)
      .slice(0, 15);
    return sorted;
  }, [forecastValues]);

  // Build scatter-ready data for beeswarm: one point per (feature, step) with jitter
  const scatterData = useMemo(() => {
    if (!shapData) return [];
    const result: Array<{ feat: string; shap: number; row: number }> = [];
    shapData.forEach(({ feat, vals }) => {
      for (const v of vals) {
        result.push({ feat, shap: v.value, row: 0 });
      }
    });
    return result;
  }, [shapData]);

  // Training-level importance
  const importanceData = useMemo(() => {
    if (!featureImportance) return [];
    const entries = Object.entries(featureImportance)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 20);
    const maxVal = entries.length > 0 ? entries[0][1] : 1;
    return entries.map(([name, val]) => ({
      name,
      importance: val,
      pct: (val / maxVal) * 100,
    }));
  }, [featureImportance]);

  const hasShap = shapData !== null && shapData.length > 0;

  if (importanceData.length === 0 && !hasShap) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Feature importance {modelName ? `(${modelName})` : ''}
          </Typography>
          {hasShap && (
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <Select value={view} onChange={(e) => setView(e.target.value as 'importance' | 'shap')}>
                <MenuItem value="importance">Training importance</MenuItem>
                <MenuItem value="shap">Per-step SHAP</MenuItem>
              </Select>
            </FormControl>
          )}
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
          {view === 'importance' ? 'Which features drive the forecast most (training-level)' : 'Per-step SHAP contributions across all forecast dates'}
        </Typography>
        {view === 'importance' && importanceData.length > 0 && (
          <Box sx={{ width: '100%', height: Math.max(200, importanceData.length * 24) }}>
            <ResponsiveContainer>
              <BarChart data={importanceData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={140} tickFormatter={(v: string) => v.replace(/_/g, ' ')} />
                <Tooltip formatter={(_: unknown, name: string) => [name === 'importance' ? `Importance: ${Number(_).toFixed(1)}` : `${Number(_).toFixed(0)}%`, '']} />
                <Bar dataKey="pct" fill={theme.palette.primary.main} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        )}
        {view === 'shap' && hasShap && (
          <Box sx={{ width: '100%', height: Math.max(200, shapData.length * 28) }}>
            <ResponsiveContainer>
              <ScatterChart margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="shap" name="SHAP contribution" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="feat" name="Feature" tick={{ fontSize: 11 }} width={140} tickFormatter={(v: string) => v.replace(/_/g, ' ')} />
                <ZAxis range={[16, 16]} />
                <Tooltip formatter={(value: unknown, name: string) => [Number(value).toFixed(3), name === 'shap' ? 'SHAP' : '']} />
                <Scatter data={scatterData} fill={theme.palette.primary.main} opacity={0.6} shape="circle" />
              </ScatterChart>
            </ResponsiveContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
