import { render, screen } from '@testing-library/react'
import { Sidebar } from '@/components/sidebar'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/graph',
}))

describe('Sidebar', () => {
  it('renders all nav links', () => {
    render(<Sidebar />)
    expect(screen.getByText('Graph')).toBeInTheDocument()
    expect(screen.getByText('Sessions')).toBeInTheDocument()
    expect(screen.getByText('Code')).toBeInTheDocument()
    expect(screen.getByText('Stats')).toBeInTheDocument()
  })
})
