import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NodeDetail } from '@/components/node-detail'

const mockNode = {
  id: 'abc',
  name: 'AuthService',
  entityType: 'TechDecision',
  created_at: '2026-03-26T10:00:00Z',
  summary: 'Decided to use JWT tokens',
}

describe('NodeDetail', () => {
  it('renders node name and type', () => {
    render(
      <NodeDetail node={mockNode} connections={[]} onClose={() => {}} />
    )
    expect(screen.getByText('AuthService')).toBeInTheDocument()
    expect(screen.getByText('TechDecision')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', async () => {
    const onClose = jest.fn()
    render(
      <NodeDetail node={mockNode} connections={[]} onClose={onClose} />
    )
    await userEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
