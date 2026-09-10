import type { Category } from '../api/categories'

/** Display-only relabeling — no backend/data rename, avoids churn for zero benefit. */
export function classificationLabel(classification: Category['classification']): string {
  if (classification === 'Expense') return 'Business Expense'
  return classification
}

export interface CategoryGroup {
  label: string
  categories: Category[]
}

/** Groups the flat category list into the option-groups relevant to a given
 * transaction type, so an Income entry can't accidentally be filed under a
 * Relief or Capital Asset category and vice versa.
 */
export function groupCategoriesForType(categories: Category[], transactionType: 'income' | 'expense'): CategoryGroup[] {
  if (transactionType === 'income') {
    return [
      { label: 'Income', categories: categories.filter((c) => c.classification === 'Income') },
      { label: 'Other Income', categories: categories.filter((c) => c.developer_slug === 'other_income') },
    ].filter((group) => group.categories.length > 0)
  }

  return [
    { label: 'Business Expenses', categories: categories.filter((c) => c.classification === 'Expense') },
    { label: 'Reliefs', categories: categories.filter((c) => c.classification === 'Relief') },
    { label: 'Capital Assets', categories: categories.filter((c) => c.classification === 'Asset') },
    { label: 'Other', categories: categories.filter((c) => c.developer_slug === 'other_expense') },
  ].filter((group) => group.categories.length > 0)
}
