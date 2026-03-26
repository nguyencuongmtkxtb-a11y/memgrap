'use client'

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface ProjectContextValue {
  project: string | null
  setProject: (p: string | null) => void
}

const ProjectContext = createContext<ProjectContextValue>({
  project: null,
  setProject: () => {},
})

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [project, setProjectState] = useState<string | null>(null)

  useEffect(() => {
    const saved = localStorage.getItem('memgrap-project')
    if (saved) setProjectState(saved)
  }, [])

  const setProject = (p: string | null) => {
    setProjectState(p)
    if (p) {
      localStorage.setItem('memgrap-project', p)
    } else {
      localStorage.removeItem('memgrap-project')
    }
  }

  return (
    <ProjectContext.Provider value={{ project, setProject }}>
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  return useContext(ProjectContext)
}
