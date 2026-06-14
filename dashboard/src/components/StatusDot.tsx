import { Box } from '@mui/material';

interface StatusDotProps {
  status: string;
  size?: number;
  pulse?: boolean;
}

const statusColors: Record<string, string> = {
  healthy: '#00e676', online: '#00e676', running: '#00e676',
  degraded: '#ff9100', warning: '#ff9100', acknowledged: '#ff9100',
  critical: '#ff1744', error: '#ff1744',
  offline: '#4a5568', disconnected: '#4a5568',
  unknown: '#8896a6', resolved: '#8896a6',
};

export default function StatusDot({ status, size = 10, pulse = false }: StatusDotProps) {
  const color = statusColors[status.toLowerCase()] ?? statusColors.unknown;
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: color,
        boxShadow: pulse ? `0 0 ${size * 2}px ${color}60` : `0 0 6px ${color}40`,
        animation: pulse ? 'pulse 2s infinite' : 'none',
        '@keyframes pulse': {
          '0%': { boxShadow: `0 0 0 0 ${color}80` },
          '70%': { boxShadow: `0 0 0 ${size * 2}px ${color}00` },
          '100%': { boxShadow: `0 0 0 0 ${color}00` },
        },
      }}
    />
  );
}