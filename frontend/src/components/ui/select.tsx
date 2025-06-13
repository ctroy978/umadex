import React, { createContext, useContext, useState, Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/24/outline';

interface SelectContextType {
  value: string;
  onValueChange: (value: string) => void;
  options: Array<{ value: string; label: React.ReactNode }>;
  setOptions: React.Dispatch<React.SetStateAction<Array<{ value: string; label: React.ReactNode }>>>;
}

const SelectContext = createContext<SelectContextType | null>(null);

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

interface SelectItemProps {
  value: string;
  children: React.ReactNode;
}

export function Select({ value, onValueChange, children }: SelectProps) {
  const [options, setOptions] = useState<Array<{ value: string; label: React.ReactNode }>>([]);

  // Extract options from children on mount/change
  React.useEffect(() => {
    const extractedOptions: Array<{ value: string; label: React.ReactNode }> = [];
    
    const findSelectItems = (children: React.ReactNode) => {
      React.Children.forEach(children, (child) => {
        if (React.isValidElement(child)) {
          if (child.props.value !== undefined) {
            extractedOptions.push({
              value: child.props.value,
              label: child.props.children,
            });
          } else if (child.props.children) {
            findSelectItems(child.props.children);
          }
        }
      });
    };
    
    findSelectItems(children);
    setOptions(extractedOptions);
  }, [children]);

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <SelectContext.Provider value={{ value, onValueChange, options, setOptions }}>
      <Listbox value={value} onChange={onValueChange}>
        <div className="relative">
          <Listbox.Button className="relative w-full cursor-default rounded-md bg-white py-2 pl-3 pr-10 text-left shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-600 sm:text-sm">
            <span className="block truncate">{selectedOption?.label || 'Select...'}</span>
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </span>
          </Listbox.Button>
          
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
              {options.map((option) => (
                <Listbox.Option
                  key={option.value}
                  className={({ active }) =>
                    `relative cursor-default select-none py-2 pl-10 pr-4 ${
                      active ? 'bg-blue-100 text-blue-900' : 'text-gray-900'
                    }`
                  }
                  value={option.value}
                >
                  {({ selected }) => (
                    <>
                      <span className={`block truncate ${selected ? 'font-medium' : 'font-normal'}`}>
                        {option.label}
                      </span>
                      {selected ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                          <CheckIcon className="h-5 w-5" aria-hidden="true" />
                        </span>
                      ) : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
    </SelectContext.Provider>
  );
}

export function SelectTrigger({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  // This component is handled by the main Select component
  return null;
}

export function SelectContent({ children }: { children: React.ReactNode }) {
  // This component is handled by the main Select component
  return null;
}

export function SelectItem({ value, children }: SelectItemProps) {
  // This component is just used to provide structure for Select to extract options
  return null;
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  // This component is handled by the main Select component
  return null;
}