import { useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'

interface FieldWrapperProps {
  label: string
  children: ReactNode
}

function FieldWrapper({ label, children }: FieldWrapperProps) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold text-on-surface-variant">{label}</span>
      {children}
    </label>
  )
}

const inputClasses =
  'h-12 w-full rounded-lg border border-outline-variant bg-white px-4 text-sm focus:border-blue focus:outline-none focus:ring-1 focus:ring-blue'

export function TextField({ label, ...rest }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldWrapper label={label}>
      <input className={inputClasses} {...rest} />
    </FieldWrapper>
  )
}

export function PasswordField({
  label,
  ...rest
}: { label: string } & Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  const [visible, setVisible] = useState(false)

  return (
    <FieldWrapper label={label}>
      <div className="relative">
        <input {...rest} type={visible ? 'text' : 'password'} className={`${inputClasses} pr-11`} />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-on-surface-variant hover:text-on-surface"
        >
          <span className="material-symbols-outlined text-lg">{visible ? 'visibility_off' : 'visibility'}</span>
        </button>
      </div>
    </FieldWrapper>
  )
}

export function SelectField({
  label,
  children,
  ...rest
}: { label: string; children: ReactNode } & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldWrapper label={label}>
      <select className={inputClasses} {...rest}>
        {children}
      </select>
    </FieldWrapper>
  )
}
