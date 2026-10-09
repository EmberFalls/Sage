import React, { ReactNode } from 'react'

interface SectionHeadingProps {
  tag?: string
  title: string
  subtitle?: string
  centered?: boolean
  badge?: ReactNode
}

export function SectionHeading({ tag, title, subtitle, centered = true, badge }: SectionHeadingProps) {
  return (
    <div className={`landing-section-heading ${centered ? 'text-center' : ''}`}>
      {tag && (
        <div className="landing-tag-wrapper">
          <span className="landing-category-tag">{tag}</span>
          {badge}
        </div>
      )}
      <h2 className="landing-heading-title">{title}</h2>
      {subtitle && <p className="landing-heading-subtitle">{subtitle}</p>}
    </div>
  )
}
