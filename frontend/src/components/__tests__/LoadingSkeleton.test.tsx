import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { LoadingSkeleton } from '../LoadingSkeleton'

describe('LoadingSkeleton', () => {
  it('renders card skeleton by default with 3 bars', () => {
    const { container } = render(<LoadingSkeleton />)
    const bars = container.querySelectorAll('.skeleton-shimmer')
    expect(bars).toHaveLength(3)
  })

  it('renders table skeleton with header row and correct data rows', () => {
    const { container } = render(<LoadingSkeleton type="table" rows={2} />)
    const bars = container.querySelectorAll('.skeleton-shimmer')
    // header row (5) + 2 data rows (5 each) = 15
    expect(bars).toHaveLength(15)
  })

  it('renders widget skeleton with 4 bars', () => {
    const { container } = render(<LoadingSkeleton type="widget" />)
    const bars = container.querySelectorAll('.skeleton-shimmer')
    expect(bars).toHaveLength(4)
  })
})
