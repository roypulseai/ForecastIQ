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
  MenuItem,
  Select,
  Snackbar,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AddIcon from '@mui/icons-material/Add';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { PageContainer } from '../components/layout/PageContainer';
import { useCreateApiKey, useDeleteApiKey, useListApiKeys, useUpdateApiKey, useListApiKeyTiers } from '../hooks/useApiKeys';
import { getErrorMessage } from '../services/api';
import { formatDate } from '../utils/format';
import type { ApiKeyRecord, ApiKeyTier } from '../types';

export function ApiKeysPage(): ReactNode {
  const list = useListApiKeys();
  const tiers = useListApiKeyTiers();
  const createMut = useCreateApiKey();
  const updateMut = useUpdateApiKey();
  const deleteMut = useDeleteApiKey();
  const [createOpen, setCreateOpen] = useState(false);
  const [newlyCreated, setNewlyCreated] = useState<{ plain_key: string; prefix: string; warning: string } | null>(null);
  const [editTarget, setEditTarget] = useState<ApiKeyRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const items = useMemo(() => list.data?.items ?? [], [list.data]);

  const tierMap = useMemo(() => {
    const m = new Map<ApiKeyTier, number>();
    tiers.data?.tiers.forEach((t) => m.set(t.tier, t.rate_limit_per_minute));
    return m;
  }, [tiers.data]);

  const handleCreate = async (params: { name: string; tier: ApiKeyTier; expires_at: string }) => {
    setError(null);
    try {
      const res = await createMut.mutateAsync(params);
      setCreateOpen(false);
      setNewlyCreated({ plain_key: res.plain_key, prefix: res.prefix, warning: res.warning });
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleRevoke = async (key: ApiKeyRecord) => {
    if (!window.confirm(`Revoke API key "${key.name}"? This cannot be undone.`)) return;
    try {
      await deleteMut.mutateAsync(key.key_id);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      setError('Could not copy to clipboard');
    }
  };

  return (
    <PageContainer
      title="API keys"
      subtitle="Programmatic access to ForecastIQ for notebooks, scripts, and other tools. Authenticate with a key in the Authorization header."
      actions={
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
        >
          New API key
        </Button>
      }
    >
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={2}>
            <VpnKeyIcon color="primary" />
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Quickstart</Typography>
              <Typography variant="body2" color="text.secondary">
                Pass your key as{' '}
                <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                  Authorization: Bearer fiq_live_...
                </code>{' '}
                or{' '}
                <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                  X-API-Key: fiq_live_...
                </code>
                . Base URL:{' '}
                <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                  {window.location.origin}/v1
                </code>
              </Typography>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {list.isLoading ? (
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading keys…</Typography>
        </Stack>
      ) : items.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <VpnKeyIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            No API keys yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create one to start calling ForecastIQ from notebooks, scripts, and other tools.
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
            New API key
          </Button>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {items.map((k) => (
            <Grid key={k.key_id} item xs={12} md={6}>
              <Card sx={{ height: '100%', opacity: k.revoked ? 0.6 : 1 }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }} noWrap>
                        {k.name}
                      </Typography>
                      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                        <Chip label={k.prefix} size="small" variant="outlined" />
                        <Chip
                          label={k.tier}
                          size="small"
                          color={k.tier === 'free' ? 'default' : k.tier === 'pro' ? 'primary' : 'secondary'}
                        />
                        {k.revoked && <Chip label="Revoked" size="small" color="error" />}
                        {k.expires_at && (
                          <Chip
                            label={`Expires ${formatDate(k.expires_at)}`}
                            size="small"
                            variant="outlined"
                            color="warning"
                          />
                        )}
                      </Stack>
                    </Box>
                  </Stack>

                  <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 1.5, mt: 1.5 }}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Rate limit: <b>{tierMap.get(k.tier) ?? '—'}</b> requests/minute
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Created: {formatDate(k.created_at)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Last used: {k.last_used_at ? formatDate(k.last_used_at) : 'never'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Total requests: {k.request_count.toLocaleString()}
                    </Typography>
                  </Box>

                  <Stack direction="row" spacing={0.5} justifyContent="flex-end" sx={{ mt: 1.5 }}>
                    <Tooltip title="Revoke">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleRevoke(k)}
                        disabled={k.revoked}
                        aria-label={`Revoke key ${k.name}`}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Button size="small" onClick={() => setEditTarget(k)} disabled={k.revoked}>
                      Edit
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <CreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        pending={createMut.isPending}
        tiers={tiers.data?.tiers ?? []}
      />

      {newlyCreated && (
        <Dialog open onClose={() => setNewlyCreated(null)} maxWidth="sm" fullWidth>
          <DialogTitle>API key created</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              <Alert severity="warning">{newlyCreated.warning}</Alert>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Your API key
                </Typography>
                <Box
                  sx={{
                    mt: 0.5,
                    p: 1.5,
                    bgcolor: 'background.default',
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: 14,
                    wordBreak: 'break-all',
                  }}
                >
                  {newlyCreated.plain_key}
                </Box>
              </Box>
              <Typography variant="caption" color="text.secondary">
                Prefix: <b>{newlyCreated.prefix}</b> · use this for human reference (e.g. logs)
              </Typography>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              startIcon={<ContentCopyIcon />}
              onClick={() => handleCopy(newlyCreated.plain_key)}
            >
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button variant="contained" onClick={() => setNewlyCreated(null)}>
              I have stored this key
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {editTarget && (
        <EditDialog
          record={editTarget}
          onClose={() => setEditTarget(null)}
          onSave={async (updates) => {
            try {
              await updateMut.mutateAsync({ id: editTarget.key_id, updates });
              setEditTarget(null);
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
          pending={updateMut.isPending}
          tiers={tiers.data?.tiers ?? []}
        />
      )}

      <Snackbar
        open={copied}
        autoHideDuration={2000}
        onClose={() => setCopied(false)}
        message="Copied to clipboard"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </PageContainer>
  );
}

function CreateDialog({
  open,
  onClose,
  onSubmit,
  pending,
  tiers,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (params: { name: string; tier: ApiKeyTier; expires_at: string }) => void | Promise<void>;
  pending: boolean;
  tiers: Array<{ tier: ApiKeyTier; rate_limit_per_minute: number; description: string }>;
}) {
  const [name, setName] = useState('');
  const [tier, setTier] = useState<ApiKeyTier>('free');
  const [expiresAt, setExpiresAt] = useState('');
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>New API key</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            The full key is shown only once after creation. The system stores
            only a hash; you cannot retrieve the plain secret later.
          </Typography>
          <TextField
            size="small"
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Notebook, ETL pipeline"
            autoFocus
          />
          <FormControl size="small">
            <InputLabel>Tier</InputLabel>
            <Select value={tier} label="Tier" onChange={(e) => setTier(e.target.value as ApiKeyTier)}>
              {tiers.map((t) => (
                <MenuItem key={t.tier} value={t.tier}>
                  {t.tier} — {t.rate_limit_per_minute} req/min
                </MenuItem>
              ))}
              {tiers.length === 0 && <MenuItem value="free">free</MenuItem>}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Expires (optional)"
            placeholder="YYYY-MM-DD"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            helperText="Leave blank for no expiry"
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>Cancel</Button>
        <Button
          variant="contained"
          disabled={!name.trim() || pending}
          onClick={() => onSubmit({ name: name.trim(), tier, expires_at: expiresAt })}
        >
          {pending ? 'Creating…' : 'Create key'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function EditDialog({
  record,
  onClose,
  onSave,
  pending,
  tiers,
}: {
  record: ApiKeyRecord;
  onClose: () => void;
  onSave: (updates: { name?: string; tier?: ApiKeyTier; expires_at?: string }) => void | Promise<void>;
  pending: boolean;
  tiers: Array<{ tier: ApiKeyTier; rate_limit_per_minute: number; description: string }>;
}) {
  const [name, setName] = useState(record.name);
  const [tier, setTier] = useState<ApiKeyTier>(record.tier);
  const [expiresAt, setExpiresAt] = useState(record.expires_at ?? '');
  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Edit API key</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <FormControl size="small">
            <InputLabel>Tier</InputLabel>
            <Select value={tier} label="Tier" onChange={(e) => setTier(e.target.value as ApiKeyTier)}>
              {tiers.map((t) => (
                <MenuItem key={t.tier} value={t.tier}>
                  {t.tier} — {t.rate_limit_per_minute} req/min
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Expires"
            placeholder="YYYY-MM-DD (blank = never)"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>Cancel</Button>
        <Button
          variant="contained"
          disabled={pending}
          onClick={() => onSave({ name: name.trim() || record.name, tier, expires_at: expiresAt || undefined })}
        >
          {pending ? 'Saving…' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
