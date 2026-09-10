import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { getAdvisoryHistory, queryAdvisor } from '../api/advisory'
import { AppShell } from '../components/layout/AppShell'
import { ErrorBanner } from '../components/ui/Banner'
import { Spinner } from '../components/ui/Spinner'
import { ApiError } from '../lib/apiClient'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  sources?: string[]
}

const SESSION_STORAGE_KEY = 'gigtax_advisor_session_id'

const QUICK_PROMPTS = [
  'How much rent relief can I claim?',
  'What are the personal income tax bands?',
  'What expenses can I deduct as a freelancer?',
]

export function AdvisorPage() {
  const [sessionId, setSessionId] = useState<string | null>(() => sessionStorage.getItem(SESSION_STORAGE_KEY))
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const historyQuery = useQuery({
    queryKey: ['advisory-history', sessionId],
    queryFn: () => getAdvisoryHistory(sessionId as string),
    enabled: !!sessionId,
  })

  useEffect(() => {
    if (historyQuery.data) {
      const restored: ChatMessage[] = historyQuery.data.flatMap((turn) => [
        { id: `${turn.query_id}-q`, role: 'user' as const, text: turn.query_text },
        { id: `${turn.query_id}-a`, role: 'assistant' as const, text: turn.response_text, sources: turn.sources },
      ])
      setMessages(restored)
    }
  }, [historyQuery.data])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const askMutation = useMutation({
    mutationFn: (question: string) => queryAdvisor(question, sessionId ?? undefined),
    onSuccess: (data, question) => {
      setSessionId(data.session_id)
      sessionStorage.setItem(SESSION_STORAGE_KEY, data.session_id)
      setMessages((prev) => [
        ...prev,
        { id: `${data.query_id}-a`, role: 'assistant', text: data.answer, sources: data.sources },
      ])
      void question
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not reach the advisor.'),
  })

  function send(question: string) {
    if (!question.trim() || askMutation.isPending) return
    setError(null)
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: 'user', text: question }])
    setInput('')
    askMutation.mutate(question)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  function startNewChat() {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    setMessages([])
  }

  return (
    <AppShell title="AI Tax Advisor">
      <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg bg-surface-container-lowest shadow-level-1 md:h-[calc(100vh-6rem)]">
        <div className="flex items-center justify-between border-b border-outline-variant px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined fill text-2xl text-blue">smart_toy</span>
            <div>
              <p className="font-semibold text-navy">Ada</p>
              <p className="text-xs text-on-surface-variant">AI Tax Advisor</p>
            </div>
          </div>
          <button onClick={startNewChat} className="text-sm text-blue hover:underline">
            New chat
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {historyQuery.isLoading && <Spinner size={24} />}
          {messages.length === 0 && !historyQuery.isLoading && (
            <p className="text-center text-sm italic text-on-surface-variant">
              Ask a question about your taxes under the Nigeria Tax Act 2025.
            </p>
          )}
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                  message.role === 'user' ? 'bg-navy text-white' : 'bg-surface-container text-on-surface'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="markdown-content">
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{message.text}</p>
                )}
                {message.sources && message.sources.length > 0 && (
                  <p className="mt-2 text-xs opacity-70">Sources: {message.sources.join(', ')}</p>
                )}
              </div>
            </div>
          ))}
          {askMutation.isPending && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-lg bg-surface-container px-4 py-2.5 text-sm text-on-surface-variant">
                <Spinner size={14} />
                Ada is thinking...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {error && (
          <div className="px-4 pb-2">
            <ErrorBanner message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        <div className="border-t border-outline-variant p-4">
          <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => send(prompt)}
                className="shrink-0 rounded-full border border-outline-variant px-3 py-1.5 text-xs text-on-surface-variant hover:bg-surface-container-low"
              >
                {prompt}
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send(input)
                }
              }}
              rows={1}
              placeholder="Ask about your taxes..."
              className="max-h-32 flex-1 resize-none rounded-lg border border-outline-variant px-4 py-2.5 text-sm focus:border-blue focus:outline-none"
            />
            <button
              type="submit"
              disabled={askMutation.isPending || !input.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue text-white disabled:bg-blue/50"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </form>
          <p className="mt-2 text-center text-xs text-on-surface-variant">
            Ada can make mistakes. Consider verifying important tax information.
          </p>
        </div>
      </div>
    </AppShell>
  )
}
