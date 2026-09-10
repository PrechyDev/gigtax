import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

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
