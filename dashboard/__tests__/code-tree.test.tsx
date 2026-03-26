import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeTree } from '@/components/code-tree'

const mockFiles = [
  {
    _id: 'f1',
    path: 'src/auth.py',
    language: 'python',
    children: [
      { _id: 'c1', name: 'login', type: 'CodeFunction', line: 10 },
      { _id: 'c2', name: 'AuthClass', type: 'CodeClass', line: 1 },
    ],
  },
]

describe('CodeTree', () => {
  it('renders file path', () => {
    render(<CodeTree files={mockFiles} />)
    expect(screen.getByText('src/auth.py')).toBeInTheDocument()
  })

  it('toggles children on click', async () => {
    render(<CodeTree files={mockFiles} />)
    expect(screen.queryByText('login')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('src/auth.py'))
    expect(screen.getByText('login')).toBeInTheDocument()
    expect(screen.getByText('AuthClass')).toBeInTheDocument()
  })
})
