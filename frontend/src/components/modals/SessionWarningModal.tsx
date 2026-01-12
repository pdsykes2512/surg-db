import { useEffect, useState } from 'react'

interface SessionWarningModalProps {
  isOpen: boolean
  timeRemaining: number // seconds
  onExtend: () => void
  onLogout: () => void
}

export function SessionWarningModal({ isOpen, timeRemaining, onExtend, onLogout }: SessionWarningModalProps) {
  const [seconds, setSeconds] = useState(timeRemaining)

  useEffect(() => {
    setSeconds(timeRemaining)
  }, [timeRemaining])

  useEffect(() => {
    if (!isOpen) return

    const interval = setInterval(() => {
      setSeconds(prev => {
        if (prev <= 1) {
          clearInterval(interval)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isOpen])

  if (!isOpen) return null

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  const timeDisplay = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[200]"
      style={{ margin: 0 }}
    >
      <div className="bg-white rounded-lg max-w-md w-full mx-4 shadow-xl">
        {/* Header */}
        <div className="bg-amber-500 px-6 py-4 rounded-t-lg">
          <div className="flex items-center gap-3">
            <div className="text-white text-2xl">⏰</div>
            <h2 className="text-xl font-semibold text-white">Session Timeout Warning</h2>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="text-center">
            <div className="text-5xl font-bold text-amber-600 mb-2">
              {timeDisplay}
            </div>
            <p className="text-gray-700">
              Your session will expire due to inactivity.
            </p>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-800">
              <strong>Why am I seeing this?</strong>
              <br />
              For security reasons, your session will automatically end after 30 minutes of inactivity.
            </p>
          </div>

          <div className="space-y-2 text-sm text-gray-600">
            <p>• Click <strong>Continue Session</strong> to stay logged in</p>
            <p>• Click <strong>Logout Now</strong> to end your session</p>
            <p>• If no action is taken, you'll be automatically logged out</p>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 rounded-b-lg flex justify-between gap-3">
          <button
            onClick={onLogout}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
          >
            Logout Now
          </button>
          <button
            onClick={onExtend}
            className="px-6 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Continue Session
          </button>
        </div>
      </div>
    </div>
  )
}
