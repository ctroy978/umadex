import * as React from "react"
import { cn } from "@/lib/utils"

interface RadioGroupProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  className?: string
}

const RadioGroup = React.forwardRef<HTMLDivElement, RadioGroupProps>(
  ({ value, onValueChange, children, className, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("grid gap-2", className)} {...props}>
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child, { value, onValueChange } as any)
          }
          return child
        })}
      </div>
    )
  }
)
RadioGroup.displayName = "RadioGroup"

interface RadioGroupItemProps {
  value: string
  id?: string
  className?: string
  checked?: boolean
  onValueChange?: (value: string) => void
}

const RadioGroupItem = React.forwardRef<HTMLInputElement, RadioGroupItemProps>(
  ({ className, value: itemValue, onValueChange, ...props }, ref) => {
    return (
      <input
        type="radio"
        ref={ref}
        value={itemValue}
        onChange={() => onValueChange?.(itemValue)}
        className={cn(
          "h-4 w-4 text-primary focus:ring-primary border-gray-300",
          className
        )}
        {...props}
      />
    )
  }
)
RadioGroupItem.displayName = "RadioGroupItem"

export { RadioGroup, RadioGroupItem }