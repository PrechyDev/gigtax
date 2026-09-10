import type { ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  isLoading?: boolean
}

const VARIANT_CLASSES: Record<string, string> = {
  primary: 'bg-blue text-white hover:bg-blue-dark disabled:bg-blue/50',
  secondary: 'border border-outline-variant bg-white text-on-surface hover:bg-surface-container-low',
  danger: 'bg-error text-white hover:bg-error/90 disabled:bg-error/50',
}

/** Every submit button in the app goes through this — spinner + disabled state is
 * automatic from `isLoading`, so no page hand-rolls its own loading treatment.
 */
export function Button({ variant = 'primary', isLoading, disabled, children, className = '', ...rest }: ButtonProps) {
  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...rest}
    >
      {isLoading && <Spinner size={16} className={variant === 'secondary' ? 'border-blue' : 'border-white'} />}
      {children}
    </button>
  )
}
