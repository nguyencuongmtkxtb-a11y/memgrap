'use client'

import { useEffect, useState, useCallback } from 'react'
import { Key, Database, Info, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ErrorBanner } from '@/components/error-banner'
import { ErrorBoundary } from '@/components/error-boundary'

interface SettingsData {
  openai: { maskedKey: string; isSet: boolean }
  neo4j: { uri: string; user: string; status: 'ok' | 'error'; detail: string }
  system: { llmModel: string; embeddingModel: string }
}

interface TestResult {
  valid: boolean
  modelCount?: number
  error?: string
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // OpenAI test state
  const [testKey, setTestKey] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  // Neo4j test state
  const [testingNeo4j, setTestingNeo4j] = useState(false)
  const [neo4jTestDone, setNeo4jTestDone] = useState(false)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await fetch('/api/settings')
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  async function handleTestNeo4j() {
    setTestingNeo4j(true)
    setNeo4jTestDone(false)
    try {
      const res = await fetch('/api/settings')
      if (!res.ok) throw new Error()
      setData(await res.json())
      setNeo4jTestDone(true)
    } catch {
      setError(true)
    } finally {
      setTestingNeo4j(false)
    }
  }

  useEffect(() => { fetchSettings() }, [fetchSettings])

  async function handleTestKey() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/settings/test-openai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: testKey || undefined }),
      })
      setTestResult(await res.json())
    } catch {
      setTestResult({ valid: false, error: 'Network error' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 max-w-3xl">
        <h1 className="text-xl font-semibold mb-6">Settings</h1>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="p-8 max-w-3xl space-y-6">
        <h1 className="text-xl font-semibold">Settings</h1>
        {error && <ErrorBanner />}

        {/* OpenAI API Key */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4" /> OpenAI API Key
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <code className="text-sm bg-muted px-2 py-1 rounded">
                {data?.openai.maskedKey ?? '(unknown)'}
              </code>
              <Badge variant={data?.openai.isSet ? 'default' : 'destructive'}>
                {data?.openai.isSet ? 'Set' : 'Not Set'}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Input
                type="password"
                placeholder="Paste key to test (or leave empty to test env key)"
                value={testKey}
                onChange={(e) => setTestKey(e.target.value)}
                className="flex-1"
              />
              <Button onClick={handleTestKey} disabled={testing} size="sm">
                {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Test Key'}
              </Button>
            </div>
            {testResult && (
              <div className="flex items-center gap-2 text-sm">
                {testResult.valid ? (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-green-600">
                      Valid — {testResult.modelCount} models available
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-red-500" />
                    <span className="text-red-600">{testResult.error}</span>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Neo4j Connection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" /> Neo4j Connection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">URI</span>
              <code className="bg-muted px-2 py-0.5 rounded">{data?.neo4j.uri}</code>
              <span className="text-muted-foreground">User</span>
              <code className="bg-muted px-2 py-0.5 rounded">{data?.neo4j.user}</code>
              <span className="text-muted-foreground">Status</span>
              <div>
                <Badge variant={data?.neo4j.status === 'ok' ? 'default' : 'destructive'}>
                  {data?.neo4j.status === 'ok' ? 'Connected' : 'Disconnected'}
                </Badge>
              </div>
            </div>
            {data?.neo4j.detail && (
              <p className="text-xs text-red-500">{data.neo4j.detail}</p>
            )}
            <div className="flex items-center gap-2">
              <Button onClick={handleTestNeo4j} disabled={testingNeo4j} size="sm" variant="outline">
                {testingNeo4j ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Test Connection'}
              </Button>
              {neo4jTestDone && data?.neo4j.status === 'ok' && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" /> Connected
                </span>
              )}
              {neo4jTestDone && data?.neo4j.status === 'error' && (
                <span className="flex items-center gap-1 text-sm text-red-600">
                  <XCircle className="h-4 w-4" /> Failed
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* System Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Info className="h-4 w-4" /> System Info
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">LLM Model</span>
              <code className="bg-muted px-2 py-0.5 rounded">{data?.system.llmModel}</code>
              <span className="text-muted-foreground">Embedding Model</span>
              <code className="bg-muted px-2 py-0.5 rounded">{data?.system.embeddingModel}</code>
            </div>
          </CardContent>
        </Card>
      </div>
    </ErrorBoundary>
  )
}
