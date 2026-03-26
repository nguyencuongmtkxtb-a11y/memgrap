import { render, screen } from '@testing-library/react'
import { StatCards } from '@/components/stat-cards'

const mockStats = {
  entityCount: 42,
  edgeCount: 108,
  sessionCount: 7,
  codeFileCount: 23,
  recentEpisodes: [
    {
      _id: '1',
      content: 'Remembered a decision about auth',
      created_at: '2026-03-26T10:00:00Z',
    },
  ],
  health: { neo4j: 'ok', groupId: 'test-proj', llmModel: 'gpt-4o-mini' },
}

describe('StatCards', () => {
  it('renders count cards', () => {
    render(<StatCards stats={mockStats} />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('108')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('23')).toBeInTheDocument()
  })

  it('shows health status', () => {
    render(<StatCards stats={mockStats} />)
    expect(screen.getByText('test-proj')).toBeInTheDocument()
  })
})
