import { Chip } from '@mui/material';

interface AlertBadgeProps {
  severity: string;
  size?: 'small' | 'medium';
}

const config: Record<string, { color: 'success' | 'warning' | 'error' | 'info'; label: string; bg: string }> = {
  low:       { color: 'success', label: 'LOW',      bg: 'rgba(0, 230, 118, 0.15)' },
  medium:    { color: 'warning', label: 'MEDIUM',   bg: 'rgba(255, 145, 0, 0.15)' },
  high:      { color: 'error',   label: 'HIGH',      bg: 'rgba(255, 23, 68, 0.15)' },
  critical:  { color: 'error',   label: 'CRITICAL',  bg: 'rgba(255, 23, 68, 0.30)' },
};

export default function AlertBadge({ severity, size = 'small' }: AlertBadgeProps) {
  const { color, label } = config[severity.toLowerCase()] ?? config.low;
  return (
    <Chip
      label={label}
      color={color}
      size={size}
      variant={severity === 'critical' ? 'filled' : 'outlined'}
      sx={{
        fontWeight: 700,
        fontSize: size === 'small' ? '0.68rem' : '0.75rem',
        letterSpacing: '0.05em',
        borderWidth: severity === 'low' ? 1 : 0,
      }}
    />
  );
}