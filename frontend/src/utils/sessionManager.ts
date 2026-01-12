/**
 * Session Manager
 * Handles session timeout, activity tracking, and automatic token refresh
 */

interface SessionConfig {
  timeoutMinutes: number  // Session timeout in minutes
  warningMinutes: number  // Warning before timeout in minutes
  refreshThresholdMinutes: number  // Refresh token when this many minutes remain
}

export type SessionEventType = 'warning' | 'timeout' | 'refreshed'

export type SessionEventHandler = (event: SessionEventType) => void

class SessionManager {
  private config: SessionConfig
  private lastActivityTime: number
  private warningTimer: NodeJS.Timeout | null = null
  private timeoutTimer: NodeJS.Timeout | null = null
  private checkInterval: NodeJS.Timeout | null = null
  private eventHandlers: SessionEventHandler[] = []
  private isActive: boolean = false
  
  constructor(config: SessionConfig) {
    this.config = config
    this.lastActivityTime = Date.now()
  }
  
  /**
   * Start session monitoring
   */
  start(): void {
    if (this.isActive) return
    
    this.isActive = true
    this.lastActivityTime = Date.now()
    
    // Set up activity listeners
    this.setupActivityListeners()
    
    // Check session status every 30 seconds
    this.checkInterval = setInterval(() => {
      this.checkSessionStatus()
    }, 30000)
  }
  
  /**
   * Stop session monitoring
   */
  stop(): void {
    this.isActive = false
    this.removeActivityListeners()
    
    if (this.warningTimer) {
      clearTimeout(this.warningTimer)
      this.warningTimer = null
    }
    
    if (this.timeoutTimer) {
      clearTimeout(this.timeoutTimer)
      this.timeoutTimer = null
    }
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }
  
  /**
   * Register event handler
   */
  on(handler: SessionEventHandler): void {
    this.eventHandlers.push(handler)
  }
  
  /**
   * Remove event handler
   */
  off(handler: SessionEventHandler): void {
    this.eventHandlers = this.eventHandlers.filter(h => h !== handler)
  }
  
  /**
   * Update last activity time
   */
  recordActivity(): void {
    this.lastActivityTime = Date.now()
    
    // Clear existing timers when user is active
    if (this.warningTimer) {
      clearTimeout(this.warningTimer)
      this.warningTimer = null
    }
    if (this.timeoutTimer) {
      clearTimeout(this.timeoutTimer)
      this.timeoutTimer = null
    }
  }
  
  /**
   * Get time remaining until timeout (in seconds)
   */
  getTimeRemaining(): number {
    const timeoutMs = this.config.timeoutMinutes * 60 * 1000
    const elapsed = Date.now() - this.lastActivityTime
    const remaining = Math.max(0, timeoutMs - elapsed)
    return Math.floor(remaining / 1000)
  }
  
  /**
   * Get time until warning (in seconds)
   */
  getTimeUntilWarning(): number {
    const warningMs = (this.config.timeoutMinutes - this.config.warningMinutes) * 60 * 1000
    const elapsed = Date.now() - this.lastActivityTime
    const remaining = Math.max(0, warningMs - elapsed)
    return Math.floor(remaining / 1000)
  }
  
  /**
   * Check if token should be refreshed
   */
  shouldRefreshToken(): boolean {
    const timeRemaining = this.getTimeRemaining()
    const refreshThresholdSeconds = this.config.refreshThresholdMinutes * 60
    return timeRemaining > 0 && timeRemaining <= refreshThresholdSeconds
  }
  
  /**
   * Emit event to handlers
   */
  private emit(event: SessionEventType): void {
    this.eventHandlers.forEach(handler => handler(event))
  }
  
  /**
   * Check session status and emit events
   */
  private checkSessionStatus(): void {
    if (!this.isActive) return
    
    const timeRemaining = this.getTimeRemaining()
    const warningSeconds = this.config.warningMinutes * 60
    
    // Session has timed out
    if (timeRemaining === 0) {
      this.emit('timeout')
      this.stop()
      return
    }
    
    // Show warning if within warning window
    if (timeRemaining <= warningSeconds && !this.warningTimer) {
      this.emit('warning')
      // Set timeout for actual timeout
      this.timeoutTimer = setTimeout(() => {
        this.emit('timeout')
        this.stop()
      }, timeRemaining * 1000)
    }
    
    // Check if token should be refreshed
    if (this.shouldRefreshToken()) {
      this.emit('refreshed')
    }
  }
  
  /**
   * Set up activity listeners
   */
  private setupActivityListeners(): void {
    const activityHandler = () => this.recordActivity()
    
    // Mouse events
    window.addEventListener('mousemove', activityHandler, { passive: true })
    window.addEventListener('mousedown', activityHandler, { passive: true })
    window.addEventListener('click', activityHandler, { passive: true })
    
    // Keyboard events
    window.addEventListener('keypress', activityHandler, { passive: true })
    window.addEventListener('keydown', activityHandler, { passive: true })
    
    // Touch events for mobile
    window.addEventListener('touchstart', activityHandler, { passive: true })
    window.addEventListener('touchmove', activityHandler, { passive: true })
    
    // Scroll events
    window.addEventListener('scroll', activityHandler, { passive: true })
    
    // Store handlers for cleanup
    ;(this as any)._activityHandler = activityHandler
  }
  
  /**
   * Remove activity listeners
   */
  private removeActivityListeners(): void {
    const activityHandler = (this as any)._activityHandler
    if (!activityHandler) return
    
    window.removeEventListener('mousemove', activityHandler)
    window.removeEventListener('mousedown', activityHandler)
    window.removeEventListener('click', activityHandler)
    window.removeEventListener('keypress', activityHandler)
    window.removeEventListener('keydown', activityHandler)
    window.removeEventListener('touchstart', activityHandler)
    window.removeEventListener('touchmove', activityHandler)
    window.removeEventListener('scroll', activityHandler)
  }
}

// Singleton instance
let sessionManager: SessionManager | null = null

/**
 * Get or create session manager instance
 */
export function getSessionManager(config?: SessionConfig): SessionManager {
  if (!sessionManager && config) {
    sessionManager = new SessionManager(config)
  }
  if (!sessionManager) {
    throw new Error('Session manager not initialized. Call with config first.')
  }
  return sessionManager
}

/**
 * Destroy session manager instance
 */
export function destroySessionManager(): void {
  if (sessionManager) {
    sessionManager.stop()
    sessionManager = null
  }
}
