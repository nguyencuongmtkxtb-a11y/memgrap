import { render, screen } from '@testing-library/react'
import { SessionList } from '@/components/session-list'

const mockSessions = [
  {
    session_id: 'abc123',
    branch: 'feat/auth',
    ended_at: '2026-03-26T10:00:00Z',
    commitCount: 3,
    filesCount: 7,
    summary: 'Implemented auth flow',
  },
]

describe('SessionList', () => {
  it('renders session row with branch and counts', () => {
    render(<SessionList sessions={mockSessions} />)
    expect(screen.getByText('feat/auth')).toBeInTheDocument()
    expect(screen.getByText('3 commits')).toBeInTheDocument()
    expect(screen.getByText('7 files')).toBeInTheDocument()
  })

  it('shows empty state when no sessions', () => {
    render(<SessionList sessions={[]} />)
    expect(screen.getByText(/no sessions/i)).toBeInTheDocument()
  })
})
