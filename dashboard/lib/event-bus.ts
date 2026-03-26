type Subscriber = (event: string, data: Record<string, unknown>) => void

class EventBus {
  private subscribers = new Set<Subscriber>()

  subscribe(fn: Subscriber): () => void {
    this.subscribers.add(fn)
    return () => {
      this.subscribers.delete(fn)
    }
  }

  publish(event: string, data: Record<string, unknown> = {}) {
    for (const fn of this.subscribers) {
      try {
        fn(event, data)
      } catch {
        /* subscriber error — do not propagate */
      }
    }
  }

  get subscriberCount() {
    return this.subscribers.size
  }
}

export const eventBus = new EventBus()
