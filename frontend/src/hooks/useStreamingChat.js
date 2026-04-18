/**
 * useStreamingChat – SSE streaming hook for the chat interface
 *
 * Manages:
 *   • Sending a message to POST /api/v1/chat/stream
 *   • Reading the SSE stream token-by-token via fetch + ReadableStream
 *   • Building the assistant reply incrementally (typewriter effect)
 *   • AbortController-based cancellation on unmount / user action
 */
import { useState, useCallback, useRef } from 'react'

const WELCOME = (name) => ({
  id: 'welcome',
  role: 'assistant',
  content: `¡Hola${name ? `, **${name.split(' ')[0]}**` : ''}! Soy **Marco**, tu asistente personal inteligente.\n\nPuedo ayudarte con:\n- 📅 **Calendario** – gestionar reuniones y eventos\n- 💰 **Finanzas** – anotar gastos y ver balances\n- 📧 **Correo** – redactar y resumir emails\n- 📁 **Nube** – consultar tus documentos\n- 🔥 **Hábitos** – seguimiento de rutinas\n\n¿En qué puedo ayudarte hoy?`,
})

export function useStreamingChat(userName) {
  const [messages, setMessages]       = useState(() => [WELCOME(userName)])
  const [isStreaming, setIsStreaming]  = useState(false)
  const [currentRoute, setCurrentRoute] = useState(null)  // {intent, label}
  const [conversationId]              = useState(() => `c-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)
  const abortRef                       = useRef(null)

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return

    // 1. Append user message + empty assistant placeholder
    const userMsgId      = `u-${Date.now()}`
    const assistantMsgId = `a-${Date.now()}`

    setMessages(prev => [
      ...prev,
      { id: userMsgId,      role: 'user',      content: trimmed },
      { id: assistantMsgId, role: 'assistant',  content: '', streaming: true },
    ])
    setIsStreaming(true)

    // 2. Open SSE stream via fetch (EventSource only supports GET)
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch('/api/v1/chat/stream', {
        method:      'POST',
        credentials: 'include',
        headers:     { 'Content-Type': 'application/json' },
        body:        JSON.stringify({ 
          message: trimmed,
          conversation_id: conversationId 
        }),
        signal:      controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? res.statusText)
      }

      // 3. Read SSE chunks
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      outer: while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decode and append to line buffer
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? '' // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()

          if (raw === '[DONE]') break outer

          try {
            const parsed = JSON.parse(raw)
            const { content, error, event, intent, label } = parsed

            // Route event from LangGraph supervisor
            if (event === 'route') {
              setCurrentRoute({ intent, label })
              continue
            }
            if (content) {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, content: m.content + content }
                    : m
                )
              )
            }
            if (error) {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, content: `⚠️ ${error}`, streaming: false }
                    : m
                )
              )
              break outer
            }
          } catch { /* skip malformed JSON */ }
        }
      }
    } catch (err) {
      // AbortError = user cancelled, don't show error
      if (err.name !== 'AbortError') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: '⚠️ No se pudo conectar con el servidor. Asegúrate de que el backend está en marcha.',
                  streaming: false,
                }
              : m
          )
        )
      }
    } finally {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId ? { ...m, streaming: false } : m
        )
      )
      setIsStreaming(false)
      setCurrentRoute(null)
      abortRef.current = null
    }
  }, [isStreaming])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { messages, setMessages, isStreaming, currentRoute, sendMessage, stopStreaming }
}
