import Link from 'next/link'
import { siteConfig } from '@/lib/site'
import { TrackedLink } from './TrackedLink'

export function IntegrationStatus({ currentProvider }: { currentProvider: 'ElevenLabs' | 'Vapi' }) {
  const otherIntegration = currentProvider === 'ElevenLabs'
    ? { href: '/integrations/vapi', label: 'Explore the Vapi integration' }
    : { href: '/integrations/elevenlabs', label: 'Explore the ElevenLabs integration' }

  return <section className="integration-status" aria-labelledby="integration-support-title">
    <p className="eyebrow">Integration support</p>
    <h2 id="integration-support-title">ElevenLabs and Vapi are supported today.</h2>
    <p>VaaniEval supports conversation imports from ElevenLabs and Vapi today. More integrations are coming soon.</p>
    <div className="inline-links">
      <TrackedLink className="button" href={siteConfig.integrationRequestUrl} event="integration_request_click" target="_blank" rel="noreferrer">Request an integration on GitHub</TrackedLink>
      <Link className="text-link" href={otherIntegration.href}>{otherIntegration.label} <span aria-hidden="true">→</span></Link>
    </div>
    <p className="integration-status-note">Please do not include credentials or private call data in an integration request.</p>
  </section>
}
