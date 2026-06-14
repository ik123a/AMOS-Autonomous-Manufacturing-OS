import { Card, CardContent, Typography, Box, CircularProgress, Tooltip } from '@mui/material';
import StatusDot from './StatusDot';

interface HealthCardProps {
  deviceId: string;
  status: string;
  lastSeen: string;
  sensorCount?: number;
  healthScore?: number;
  onClick?: () => void;
}

function getHealthColor(score?: number): string {
  if (score === undefined || score === null) return '#8896a6';
  if (score >= 90) return '#00e676';
  if (score >= 70) return '#ff9100';
  return '#ff1744';
}

function formatLastSeen(ts: string): string {
  if (!ts) return 'Unknown';
  const diff = Date.now() - new Date(ts).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

export default function HealthCard({ deviceId, status, lastSeen, sensorCount, healthScore, onClick }: HealthCardProps) {
  const healthColor = getHealthColor(healthScore);
  const score = healthScore ?? 0;

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.25s ease',
        borderColor: 'transparent',
        '&:hover': onClick ? { borderColor: '#00d4ff40', transform: 'translateY(-3px)', boxShadow: '0 8px 24px rgba(0,212,255,0.12)' } : {},
      }}
      onClick={onClick}
    >
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem' }}>
              {deviceId}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.8} mt={0.5}>
              <StatusDot status={status} size={8} />
              <Typography variant="caption" color="text.secondary" textTransform="capitalize">
                {status}
              </Typography>
            </Box>
          </Box>

          {/* Health Gauge */}
          <Tooltip title={`Health Score: ${score}%`} placement="top">
            <Box position="relative" display="inline-flex">
              <CircularProgress
                variant="determinate"
                value={score}
                size={52}
                thickness={4.5}
                sx={{ color: healthColor, '& .MuiCircularProgress-circle': { strokeLinecap: 'round' } }}
              />
              <Box
                top={0} left={0} bottom={0} right={0}
                position="absolute"
                display="flex" alignItems="center" justifyContent="center"
              >
                <Typography variant="caption" fontWeight={800} fontSize="0.72rem" color={healthColor} sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                  {score}
                </Typography>
              </Box>
            </Box>
          </Tooltip>
        </Box>

        {/* Meta */}
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="caption" color="text.secondary" display="block">
              Last seen
            </Typography>
            <Typography variant="caption" fontWeight={500} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.7rem' }}>
              {formatLastSeen(lastSeen)}
            </Typography>
          </Box>
          {sensorCount !== undefined && (
            <Box textAlign="right">
              <Typography variant="caption" color="text.secondary" display="block">
                Sensors
              </Typography>
              <Typography variant="caption" fontWeight={600} color="primary.main">
                {sensorCount}
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}