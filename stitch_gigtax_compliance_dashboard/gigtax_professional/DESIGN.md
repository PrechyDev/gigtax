---
name: GigTax Professional
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#001a42'
  on-tertiary-container: '#3980f4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#d8e2ff'
  tertiary-fixed-dim: '#adc6ff'
  on-tertiary-fixed: '#001a42'
  on-tertiary-fixed-variant: '#004395'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  stack-sm: 4px
  stack-md: 12px
  stack-lg: 24px
---

## Brand & Style
The design system is anchored in a **Corporate / Modern** aesthetic tailored specifically for the Nigerian freelance economy. It prioritizes clarity, precision, and an undeniable sense of institutional stability. The brand personality is that of a "Sophisticated Financial Partner"—expert yet accessible, replacing the anxiety of tax compliance with the confidence of professional oversight.

The visual language utilizes a "High-Utility" approach: heavy on white space to reduce cognitive load, structured layouts to manage complex data, and subtle tech-forward accents to signal modern efficiency. Every element is designed to evoke trust, ensuring that freelancers feel their financial livelihood is in secure, capable hands.

## Colors
The palette is dominated by **Deep Navy (#0F172A)**, used for high-level navigation, headings, and primary brand elements to establish authority. **Emerald Green (#10B981)** is reserved strictly for positive financial flows, tax-paid statuses, and growth indicators, acting as a psychological "reward" for compliance.

**Professional Blue (#3B82F6)** serves as the primary action color for buttons, links, and active states, distinguishing "doing" from "viewing." The background strategy employs a "layered white" approach, using **Clean White (#FFFFFF)** for interactive surfaces and **Light Gray (#F8FAFC)** for the page canvas to create a subtle sense of depth without relying on heavy borders.

## Typography
This design system utilizes **Inter** exclusively for its exceptional legibility in data-heavy environments. The typographic hierarchy is designed to guide the eye through complex financial statements. 

Headlines use tighter letter spacing and heavier weights to feel "anchored" and authoritative. Body text uses a standard 16px base for optimal readability across all devices. For numerical data in tables and dashboards, use the `tabular-nums` OpenType feature of Inter to ensure that columns of currency values align perfectly for easier visual scanning.

## Layout & Spacing
The layout follows a **Fluid Grid** system based on an 8px square baseline. 

- **Desktop:** 12-column grid with 24px gutters and a 1280px max-width container. Content is typically grouped into cards spanning 4, 6, or 12 columns.
- **Tablet:** 8-column grid with 24px gutters and 24px side margins. 
- **Mobile:** 4-column grid with 16px gutters and 16px side margins.

Horizontal spacing between related items (like icons and text) should follow the `stack-sm` or `stack-md` increments. Vertical spacing between distinct sections (like a header and a list) should utilize `stack-lg`. This ensures a breathable, professional interface that avoids the "clutter" often associated with tax software.

## Elevation & Depth
Depth is conveyed through **Tonal Layering** and **Ambient Shadows**. This design system avoids harsh borders in favor of soft, diffused shadows that lift content containers off the Light Gray (#F8FAFC) background.

- **Level 0 (Surface):** The background canvas in Light Gray.
- **Level 1 (Card):** White surfaces with a very soft, high-blur shadow (0px 4px 20px rgba(15, 23, 42, 0.05)).
- **Level 2 (Active/Hover):** Enhanced shadow for interactive cards or dropdown menus (0px 10px 30px rgba(15, 23, 42, 0.08)).

All borders, where used (such as input fields), should be low-contrast (Slate-200 / #E2E8F0) to keep the focus on the user's data.

## Shapes
The shape language is **Rounded**, utilizing a 0.5rem (8px) base radius. This strikes the perfect balance between the approachability needed for a freelancer app and the structure required for a professional tool. 

- **Buttons & Inputs:** 8px (standard)
- **Cards & Modals:** 16px (rounded-lg)
- **Badges/Chips:** Full pill (rounded-full) to distinguish them from interactive buttons.

## Components
- **Buttons:** Primary buttons use the Professional Blue (#3B82F6) with white text. High-contrast "Pay Tax" or "Submit" buttons may use Deep Navy for maximum emphasis. Secondary buttons use an outline style with a 1px Slate-200 border.
- **Input Fields:** Large, clear tap targets (48px height) with 16px horizontal padding. Labels are always persistent above the field in `label-md` style. Active states use a 2px Professional Blue border.
- **Cards:** The primary container for information. Cards must have a 16px corner radius and Level 1 elevation. For tax summaries, use a 4px left-border accent in Emerald Green to indicate a "Paid" status.
- **Professional Tables:** Minimalist design with no vertical lines. Headers use `label-md` in Deep Navy. Rows use a 1px bottom-border in #F1F5F9. For readability, use alternating "zebra" stripes in #F8FAFC on very large data sets.
- **Progress Steppers:** Essential for tax filing. Use a linear stepper with Professional Blue for the active step and Emerald Green with a checkmark for completed steps.
- **Status Chips:** Small, pill-shaped labels for "Pending," "Overdue," or "Approved." Use low-saturation background tints (e.g., light green for Emerald) with high-saturation text for readability.