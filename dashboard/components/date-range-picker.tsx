'use client'

interface Props {
  from: string
  to: string
  onChange: (from: string, to: string) => void
}

export function DateRangePicker({ from, to, onChange }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <label className="text-muted-foreground">From:</label>
      <input
        type="date"
        value={from}
        onChange={(e) => onChange(e.target.value, to)}
        className="bg-background border border-border rounded px-2 py-1 text-sm"
      />
      <label className="text-muted-foreground">To:</label>
      <input
        type="date"
        value={to}
        onChange={(e) => onChange(from, e.target.value)}
        className="bg-background border border-border rounded px-2 py-1 text-sm"
      />
      {(from || to) && (
        <button
          onClick={() => onChange('', '')}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Clear
        </button>
      )}
    </div>
  )
}
