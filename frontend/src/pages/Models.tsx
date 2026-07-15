import { useMemo, useState, type ReactNode } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Slider,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import StorageIcon from '@mui/icons-material/Storage';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ModelTrainingIcon from '@mui/icons-material/ModelTraining';
import DownloadIcon from '@mui/icons-material/Download';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import InsightsIcon from '@mui/icons-material/Insights';
import { PageContainer } from '../components/layout/PageContainer';
import {
  useDeleteSavedModel,
  useForecastWithSavedModel,
  useSavedModels,
  useTrainAndSave,
  useUpdateSavedModel,
  useUploadSavedModel,
} from '../hooks/useModels';
import { useFiles } from '../hooks/useFiles';
import { apiClient, getErrorMessage } from '../services/api';
import { downloadBlob } from '../utils/csv';
import { formatDate, formatNumber } from '../utils/format';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { useToast } from '../components/common/ToastProvider';
import { useStore } from '../store/appStore';
import { MODEL_LABELS, type Frequency, type SavedModelMeta } from '../types';

const ALL_MODEL_TYPES = ['automl', 'arima', 'sarimax', 'prophet', 'lightgbm', 'xgboost', 'wma', 'ets', 'theta', 'stl'] as const;

export function ModelsPage(): ReactNode {
  const modelsQuery = useSavedModels();
  const filesQuery = useFiles();
  const trainMut = useTrainAndSave();
  const uploadMut = useUploadSavedModel();
  const deleteMut = useDeleteSavedModel();
  const updateMut = useUpdateSavedModel();
  const forecastMut = useForecastWithSavedModel();
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [trainOpen, setTrainOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SavedModelMeta | null>(null);
  const [forecastTarget, setForecastTarget] = useState<SavedModelMeta | null>(null);
  const [forecastResult, setForecastResult] = useState<{
    model_id: string;
    forecast_values: Array<{ date: string; forecast: number; lower_ci: number; upper_ci: number; baseline?: number | null; uplift?: number | null }>;
  } | null>(null);
  const analysisData = useStore((s) => s.analysisData);
  const { showToast } = useToast();
  const [confirmDeleteModel, setConfirmDeleteModel] = useState<string | null>(null);

  const salesFile = useMemo(
    () => filesQuery.data?.find((f) => f.type === 'sales') ?? null,
    [filesQuery.data],
  );

  const items = useMemo(() => {
    let xs = modelsQuery.data?.items ?? [];
    if (filterType) xs = xs.filter((m) => m.model_type === filterType);
    if (search) {
      const q = search.toLowerCase();
      xs = xs.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.notes.toLowerCase().includes(q) ||
          m.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    return xs;
  }, [modelsQuery.data, filterType, search]);

  const handleTrain = async (params: {
    modelTypes: string[];
    trainTestSplit: number;
    horizon: number;
    name: string;
    notes: string;
    tags: string;
  }) => {
    if (!salesFile) {
      setError('Upload business data first');
      return
    }
    setError(null);
    try {
      const res = await trainMut.mutateAsync({
        models: params.modelTypes,
        file_id: salesFile.file_id,
        train_test_split: params.trainTestSplit,
        horizon: params.horizon,
        date_column: analysisData?.validation?.date_column ?? 'date',
        target_column: analysisData?.validation?.value_column ?? 'value',
        frequency: (analysisData?.validation?.frequency ?? 'D') as Frequency,
        name: params.name,
        notes: params.notes,
        tags: params.tags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      setTrainOpen(false);
      if (res.saved_model) {
        setError(null);
        // Show success briefly via a forced re-render
      }
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleUpload = async (file: File, meta: { name: string; notes: string; tags: string }) => {
    setError(null);
    try {
      await uploadMut.mutateAsync({
        file,
        meta: {
          name: meta.name || file.name,
          notes: meta.notes,
          tags: meta.tags.split(',').map((t) => t.trim()).filter(Boolean),
        },
      });
      setUploadOpen(false);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMut.mutateAsync(id);
      showToast('Model deleted', 'info');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleForecast = async (id: string, horizon: number) => {
    setError(null);
    try {
      const res = await forecastMut.mutateAsync({
        modelId: id,
        request: { horizon },
      });
      setForecastResult(res);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  return (
    <PageContainer
      title="Saved models"
      subtitle="Train once, save the artifact, then load and forecast any time without retraining. The data-science workflow."
      actions={
        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            startIcon={<CloudUploadIcon />}
            onClick={() => setUploadOpen(true)}
          >
            Upload pickle
          </Button>
          <Button
            variant="contained"
            startIcon={<ModelTrainingIcon />}
            onClick={() => { trainMut.reset(); setTrainOpen(true); }}
            disabled={!salesFile}
          >
            Train & save
          </Button>
        </Stack>
      }
    >
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!salesFile && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Upload business data to enable training new models.
        </Alert>
      )}

      {trainMut.isSuccess && trainMut.data?.saved_model && !error && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => trainMut.reset()}>
          Trained and saved <b>{trainMut.data.saved_model.name}</b> · test MAE:{' '}
          {trainMut.data.saved_model.metrics.mae != null ? trainMut.data.saved_model.metrics.mae.toFixed(2) : 'N/A'}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
            <TextField
              size="small"
              label="Search"
              placeholder="name, tag, notes…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              sx={{ flex: 1 }}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Model type</InputLabel>
              <Select
                value={filterType}
                label="Model type"
                onChange={(e) => setFilterType(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                {ALL_MODEL_TYPES.map((t) => (
                  <MenuItem key={t} value={t}>
                    {MODEL_LABELS[t] ?? t}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="body2" color="text.secondary">
              {items.length} of {modelsQuery.data?.total ?? 0} models
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      {modelsQuery.isLoading ? (
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading saved models…</Typography>
        </Stack>
      ) : items.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <StorageIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            No saved models yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Train a model with proper train/test split, or upload an existing pickle.
          </Typography>
          <Stack direction="row" spacing={1.5} justifyContent="center">
            <Button variant="outlined" startIcon={<CloudUploadIcon />} onClick={() => setUploadOpen(true)}>
              Upload pickle
            </Button>
            <Button variant="contained" startIcon={<ModelTrainingIcon />} onClick={() => { trainMut.reset(); setTrainOpen(true); }} disabled={!salesFile}>
              Train & save
            </Button>
          </Stack>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {items.map((m) => (
            <Grid key={m.model_id} item xs={12} md={6} lg={4}>
              <ModelCard
                model={m}
                onDelete={() => setConfirmDeleteModel(m.model_id)}
                onEdit={() => setEditTarget(m)}
                onForecast={() => setForecastTarget(m)}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <TrainDialog
        open={trainOpen}
        onClose={() => setTrainOpen(false)}
        onSubmit={handleTrain}
        defaultModelType="prophet"
        pending={trainMut.isPending}
        result={trainMut.data ?? null}
      />

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSubmit={handleUpload}
        pending={uploadMut.isPending}
      />

      {editTarget && (
        <EditDialog
          model={editTarget}
          onClose={() => setEditTarget(null)}
          onSave={async (updates) => {
            try {
              await updateMut.mutateAsync({ id: editTarget.model_id, updates });
              setEditTarget(null);
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
          pending={updateMut.isPending}
        />
      )}

      {forecastTarget && (
        <ForecastDialog
          model={forecastTarget}
          onClose={() => {
            setForecastTarget(null);
            setForecastResult(null);
          }}
          onForecast={handleForecast}
          pending={forecastMut.isPending}
          result={forecastResult}
        />
      )}

      <ConfirmDialog
        open={confirmDeleteModel != null}
        title="Delete saved model"
        message="Delete this saved model? This cannot be undone."
        onConfirm={() => {
          if (confirmDeleteModel) handleDelete(confirmDeleteModel);
          setConfirmDeleteModel(null);
        }}
        onCancel={() => setConfirmDeleteModel(null)}
      />
    </PageContainer>
  );
}

function ModelCard({
  model,
  onDelete,
  onEdit,
  onForecast,
}: {
  model: SavedModelMeta;
  onDelete: () => void;
  onEdit: () => void;
  onForecast: () => void;
}) {
  const handleDownload = async () => {
    const blob = await apiClient.downloadModel(model.model_id);
    downloadBlob(blob, model.name, 'application/octet-stream');
  };
  const mae = model.metrics.mae;
  const rmse = model.metrics.rmse;
  const mape = model.metrics.mape;
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }} noWrap title={model.name}>
              {model.name}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Chip
                label={MODEL_LABELS[model.model_type] ?? model.model_type.toUpperCase()}
                size="small"
                color="primary"
                variant="outlined"
              />
              <Chip
                label={model.framework}
                size="small"
                variant="outlined"
              />
            </Stack>
          </Box>
        </Stack>

        <Stack spacing={0.5} sx={{ mt: 1.5, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">Test MAE</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>{mae != null ? mae.toFixed(2) : '—'}</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">Test RMSE</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>{rmse != null ? rmse.toFixed(2) : '—'}</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">Test MAPE</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>{mape != null ? `${mape.toFixed(1)}%` : '—'}</Typography>
          </Box>
        </Stack>

        <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 1.5, mb: 1.5 }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Train: {model.train_start ?? '—'} → {model.train_end ?? '—'} ({formatNumber(model.metrics.train_rows ?? 0)} rows)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            Test:  {model.test_start ?? '—'} → {model.test_end ?? '—'} ({formatNumber(model.metrics.test_rows ?? 0)} rows)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {(model.file_size / 1024).toFixed(1)} KB · created {formatDate(model.created_at)}
          </Typography>
        </Box>

        {model.tags.length > 0 && (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mb: 1.5 }}>
            {model.tags.map((t) => (
              <Chip key={t} label={t} size="small" variant="outlined" />
            ))}
          </Stack>
        )}

        {model.notes && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, fontStyle: 'italic' }}>
            "{model.notes}"
          </Typography>
        )}

        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
          <Tooltip title="Forecast with this model">
            <IconButton size="small" onClick={onForecast} color="primary" aria-label="Forecast with this model">
              <InsightsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Edit metadata">
            <IconButton size="small" onClick={onEdit} aria-label="Edit model metadata">
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Download pickle">
            <IconButton
              size="small"
              onClick={handleDownload}
              aria-label="Download model"
            >
              <DownloadIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete">
            <IconButton size="small" onClick={onDelete} color="error" aria-label="Delete model">
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </CardContent>
    </Card>
  );
}

function TrainDialog({
  open,
  onClose,
  onSubmit,
  defaultModelType,
  pending,
  result,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (params: { modelTypes: string[]; trainTestSplit: number; horizon: number; name: string; notes: string; tags: string }) => void;
  defaultModelType: string;
  pending: boolean;
  result: import('../types').TrainResult | null;
}) {
  const [modelTypes, setModelTypes] = useState<string[]>([defaultModelType]);
  const [trainTestSplit, setTrainTestSplit] = useState(0.8);
  const [horizon, setHorizon] = useState(30);
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [tags, setTags] = useState('');

  const handle = () => {
    onSubmit({ modelTypes, trainTestSplit, horizon, name, notes, tags });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Train & save a model</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Train one or more models on a train split, evaluate on a held-out test split, and persist the best
            as a pickle. You can then load it later and forecast without retraining.
          </Typography>

          <FormControl size="small" fullWidth>
            <InputLabel>Models to train</InputLabel>
            <Select
              multiple
              value={modelTypes}
              label="Models to train"
              onChange={(e) => {
                const v = e.target.value;
                setModelTypes(typeof v === 'string' ? v.split(',') : v);
              }}
              renderValue={(selected) => (
                <Stack direction="row" spacing={0.5} flexWrap="wrap">
                  {(selected as string[]).map((m) => (
                    <Chip key={m} label={MODEL_LABELS[m] ?? m} size="small" />
                  ))}
                </Stack>
              )}
            >
              {ALL_MODEL_TYPES.map((t) => (
                <MenuItem key={t} value={t}>
                  {MODEL_LABELS[t] ?? t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Train / test split</span>
              <span><b>{Math.round(trainTestSplit * 100)}%</b> train · <b>{Math.round((1 - trainTestSplit) * 100)}%</b> test</span>
            </Typography>
            <Slider
              value={trainTestSplit}
              onChange={(_, v) => setTrainTestSplit(v as number)}
              min={0.5}
              max={0.95}
              step={0.05}
              valueLabelDisplay="auto"
              valueLabelFormat={(v) => `${Math.round(v * 100)}%`}
            />
          </Box>

          <TextField
            size="small"
            type="number"
            label="Evaluation horizon (days)"
            value={horizon}
            onChange={(e) => setHorizon(Math.max(1, Math.min(365, Number(e.target.value) || 30)))}
            helperText="Also used as test-set size when > 0"
            inputProps={{ min: 1, max: 365 }}
          />

          <TextField
            size="small"
            label="Model name (optional)"
            placeholder="e.g., Q1-2026-sales-prophet"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <TextField
            size="small"
            label="Tags (comma-separated)"
            placeholder="e.g., production, weekly, baseline"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />

          <TextField
            size="small"
            label="Notes (optional)"
            multiline
            minRows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          {pending && <LinearProgress />}

          {result && !pending && (
            <Box sx={{ p: 2, borderRadius: 1.5, bgcolor: 'background.default' }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Result
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                Split: {formatNumber(result.split.train_rows)} train / {formatNumber(result.split.test_rows)} test
              </Typography>
              {result.results.map((r, i) => (
                <Box key={i} sx={{ mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" display="block">
                    • {r.model_name.toUpperCase()}: MAE={r.metrics.mae?.toFixed(2) ?? '—'} · RMSE=
                    {r.metrics.rmse?.toFixed(2) ?? '—'} · MAPE={r.metrics.mape?.toFixed(1) ?? '—'}%
                    {r.error ? ` · error: ${r.error}` : ''}
                  </Typography>
                </Box>
              ))}
              {result.saved_model && (
                <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 1, fontWeight: 600 }}>
                  Saved: {result.saved_model.name} (id: {result.saved_model.model_id.slice(0, 8)}…)
                </Typography>
              )}
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>Cancel</Button>
        <Button variant="contained" onClick={handle} disabled={pending || modelTypes.length === 0}>
          {pending ? 'Training…' : 'Train & save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function UploadDialog({
  open,
  onClose,
  onSubmit,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (file: File, meta: { name: string; notes: string; tags: string }) => void;
  pending: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [tags, setTags] = useState('');

  const handle = () => {
    if (!file) return;
    onSubmit(file, { name, notes, tags });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload a pre-trained model</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Upload a pickle (.pkl) or joblib (.joblib) file previously produced by ForecastIQ. The model
            will be added to your registry and can be used immediately to forecast.
          </Typography>

          <Button
            variant="outlined"
            component="label"
            startIcon={<CloudUploadIcon />}
            fullWidth
          >
            {file ? file.name : 'Choose a .pkl or .joblib file'}
            <input
              type="file"
              hidden
              accept=".pkl,.joblib"
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setFile(f);
                if (f && !name) setName(f.name.replace(/\.(pkl|joblib)$/, ''));
              }}
            />
          </Button>

          <TextField
            size="small"
            label="Display name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <TextField
            size="small"
            label="Tags (comma-separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
          <TextField
            size="small"
            label="Notes (optional)"
            multiline
            minRows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          {pending && <LinearProgress />}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>Cancel</Button>
        <Button variant="contained" onClick={handle} disabled={!file || pending}>
          {pending ? 'Uploading…' : 'Upload'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function EditDialog({
  model,
  onClose,
  onSave,
  pending,
}: {
  model: SavedModelMeta;
  onClose: () => void;
  onSave: (updates: { name?: string; notes?: string; tags?: string[] }) => void | Promise<void>;
  pending: boolean;
}) {
  const [name, setName] = useState(model.name);
  const [notes, setNotes] = useState(model.notes);
  const [tags, setTags] = useState(model.tags.join(', '));
  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit model metadata</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField label="Tags (comma-separated)" size="small" value={tags} onChange={(e) => setTags(e.target.value)} />
          <TextField label="Notes" size="small" multiline minRows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
          {pending && <LinearProgress />}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => onSave({ name, notes, tags: tags.split(',').map((t) => t.trim()).filter(Boolean) })}
          disabled={pending}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function ForecastDialog({
  model,
  onClose,
  onForecast,
  pending,
  result,
}: {
  model: SavedModelMeta;
  onClose: () => void;
  onForecast: (id: string, horizon: number) => void;
  pending: boolean;
  result: { model_id: string; forecast_values: Array<{ date: string; forecast: number; lower_ci: number; upper_ci: number }> } | null;
}) {
  const [horizon, setHorizon] = useState(30);
  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Forecast with saved model</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <b>{model.name}</b> ({MODEL_LABELS[model.model_type] ?? model.model_type}) — last trained on{' '}
            {model.train_end}. Forecast will use this model directly without retraining.
          </Typography>
          <TextField
            size="small"
            type="number"
            label="Horizon (days)"
            value={horizon}
            onChange={(e) => setHorizon(Math.max(1, Math.min(3650, Number(e.target.value) || 30)))}
            inputProps={{ min: 1, max: 3650 }}
          />
          {pending && <LinearProgress />}
          {result && !pending && (
            <Box sx={{ p: 2, borderRadius: 1.5, bgcolor: 'background.default' }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Forecast ({result.forecast_values.length} points)
              </Typography>
              <Box sx={{ maxHeight: 240, overflow: 'auto' }}>
                {result.forecast_values.slice(0, 14).map((v, i) => (
                  <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.25 }}>
                    <Typography variant="caption" color="text.secondary">{v.date}</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      {v.forecast.toFixed(2)}{' '}
                      <span style={{ color: '#888' }}>
                        ({v.lower_ci.toFixed(1)}–{v.upper_ci.toFixed(1)})
                      </span>
                    </Typography>
                  </Box>
                ))}
                {result.forecast_values.length > 14 && (
                  <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
                    …and {result.forecast_values.length - 14} more
                  </Typography>
                )}
              </Box>
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button variant="contained" onClick={() => onForecast(model.model_id, horizon)} disabled={pending}>
          {pending ? 'Forecasting…' : 'Forecast'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
