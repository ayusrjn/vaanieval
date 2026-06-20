import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { listAgents, setDefaultAgent } from '../api/endpoints'
import type { ProviderAgentResponse } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { StatusPill } from '../components/StatusPill'

export function AgentsPage() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState<ProviderAgentResponse[]>([])
  const [providerFilter, setProviderFilter] = useState('all')
  const [nameFilter, setNameFilter] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const providerOptions = useMemo(() => {
    return Array.from(new Set(agents.map((agent) => agent.provider_name))).sort()
  }, [agents])

  const filteredAgents = useMemo(() => {
    const normalizedNameFilter = nameFilter.trim().toLowerCase()
    return agents.filter((agent) => {
      if (providerFilter !== 'all' && agent.provider_name !== providerFilter) {
        return false
      }
      if (normalizedNameFilter && !agent.name.toLowerCase().includes(normalizedNameFilter)) {
        return false
      }
      return true
    })
  }, [agents, nameFilter, providerFilter])

  async function handleLoad(refresh: boolean) {
    setError('')
    setLoading(true)
    try {
      const data = await listAgents({ refresh })
      setAgents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      setError('')
      setLoading(true)
      try {
        const cached = await listAgents({ refresh: false })
        if (cancelled) {
          return
        }
        setAgents(cached)
        if (cached.length === 0) {
          const refreshed = await listAgents({ refresh: true })
          if (!cancelled) {
            setAgents(refreshed)
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load agents')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  async function handleSetDefault(agentId: string) {
    setError('')
    try {
      await setDefaultAgent(agentId)
      await handleLoad(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set default agent')
    }
  }

  return (
    <section className="page agents-page">
      <PageHeader
        icon="users"
        title="Agents"
        subtitle="Pick an agent, set defaults, and jump into filtered conversation review instantly."
        className="provider-hero"
      />

      <div className="panel">
        <div className="inline">
          <button type="button" onClick={() => handleLoad(true)} disabled={loading}>
            <span className="control-with-icon">
              <FontAwesomeIcon icon="arrow-rotate-right" />
              <span>Sync agents from provider</span>
            </span>
          </button>
          <button type="button" className="secondary" onClick={() => handleLoad(false)} disabled={loading}>
            <span className="control-with-icon">
              <FontAwesomeIcon icon="clock" />
              <span>Load cached agents</span>
            </span>
          </button>
        </div>

        <div className="agents-toolbar">
          <div className="agents-filter-field">
            <label htmlFor="agent-provider-filter">Provider</label>
            <select
              id="agent-provider-filter"
              value={providerFilter}
              onChange={(event) => setProviderFilter(event.target.value)}
            >
              <option value="all">All providers</option>
              {providerOptions.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </div>

          <div className="agents-filter-field agents-filter-field-wide">
            <label htmlFor="agent-name-filter">Agent name</label>
            <input
              id="agent-name-filter"
              type="text"
              value={nameFilter}
              onChange={(event) => setNameFilter(event.target.value)}
              placeholder="Filter by agent name"
            />
          </div>
        </div>

        {loading && <p className="muted">Loading agents...</p>}
        <p className="muted">
          <FontAwesomeIcon icon="link" /> Agents are loaded across every connected provider account in your workspace.
        </p>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="panel">
        <h2>Your agents</h2>
        {agents.length === 0 ? (
          <EmptyState
            icon="headset"
            title="No agents loaded yet"
            message="Sync once to pull current providers and keep your local cache ready for future visits."
            action={
              <button type="button" onClick={() => handleLoad(true)} disabled={loading}>
                <span className="control-with-icon">
                  <FontAwesomeIcon icon="arrow-rotate-right" />
                  <span>Sync now</span>
                </span>
              </button>
            }
          />
        ) : filteredAgents.length === 0 ? (
          <EmptyState
            icon="filter"
            title="No agents match these filters"
            message="Adjust the provider or name filters to broaden the result set."
          />
        ) : (
          <div className="agents-grid">
            {filteredAgents.map((agent) => (
              <article key={agent.id} className="agent-card">
                <div className="agent-card-header">
                  <div>
                    <div className="agent-title-row">
                      <span className="agent-avatar">
                        <FontAwesomeIcon icon="robot" />
                      </span>
                      <h3>{agent.name}</h3>
                    </div>
                    <p className="muted">{agent.provider_name} voice assistant</p>
                  </div>

                  {agent.is_default ? <StatusPill icon="check-circle" label="Default" tone="success" /> : null}
                </div>

                <div className="agent-capabilities">
                  <span className="chip">
                    <FontAwesomeIcon icon="plug" />
                    <span>{agent.provider_name}</span>
                  </span>
                  <span className="chip">
                    <FontAwesomeIcon icon="wave-square" />
                    <span>Voice workflow</span>
                  </span>
                  <span className="chip">
                    <FontAwesomeIcon icon="comments" />
                    <span>Conversation review</span>
                  </span>
                </div>

                <div className="inline">
                  <button
                    type="button"
                    onClick={() =>
                      navigate(
                        `/conversations?agentId=${encodeURIComponent(agent.provider_agent_id)}&agentName=${encodeURIComponent(agent.name)}`,
                      )
                    }
                  >
                    <span className="control-with-icon">
                      <FontAwesomeIcon icon="comments" />
                      <span>View conversations</span>
                    </span>
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    disabled={agent.is_default}
                    onClick={() => handleSetDefault(agent.id)}
                  >
                    <span className="control-with-icon">
                      <FontAwesomeIcon icon="check-circle" />
                      <span>Make default</span>
                    </span>
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
