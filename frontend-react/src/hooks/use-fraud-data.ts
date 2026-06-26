import { useQuery } from '@tanstack/react-query';
import { api, agentsToKPIs, buildRiskTimeseries, type AgentsStatus, type StatsResponse } from '@/lib/api';

export function useAgentsStatus() {
  return useQuery<AgentsStatus>({
    queryKey: ['agents-status'],
    queryFn: api.agentsStatus,
    refetchInterval: 5000,
  });
}

export function useStats() {
  return useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: api.stats,
    refetchInterval: 5000,
  });
}

export function useRiskDistribution() {
  return useQuery({
    queryKey: ['risk-distribution'],
    queryFn: api.riskDistribution,
    refetchInterval: 5000,
  });
}

export function useTransactions(perPage = 50) {
  return useQuery({
    queryKey: ['transactions', perPage],
    queryFn: () => api.transactions(perPage),
    refetchInterval: 5000,
  });
}

export function useDashboardData() {
  const agents = useAgentsStatus();
  const stats = useStats();
  const risk = useRiskDistribution();
  const txns = useTransactions(30);

  const kpis = agents.data
    ? agentsToKPIs(agents.data.agents)
    : { eventsPerSec: '--', blockedToday: '--', avgDecision: '--', modelPrecision: '--' };

  const timeseries = agents.data
    ? buildRiskTimeseries(agents.data.agents)
    : [];

  const agentList = agents.data?.agents
    ? Object.entries(agents.data.agents).map(([id, a]) => ({ id, ...a }))
    : [];

  return {
    agents, stats, risk, txns,
    kpis, timeseries, agentList,
    loading: agents.isLoading || stats.isLoading,
  };
}
