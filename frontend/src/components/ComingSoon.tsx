interface ComingSoonProps {
  title: string
  description: string
  icon: React.ElementType
  color: string
}

export default function ComingSoon({ title, description, icon: Icon, color }: ComingSoonProps) {
  return (
    <div className="p-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className={`inline-flex p-4 rounded-full ${color} text-white mb-6`}>
            <Icon className="h-12 w-12" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">{title}</h1>
          <p className="text-lg text-gray-600 mb-8">{description}</p>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <p className="text-yellow-800 font-semibold mb-2">🚧 Coming Soon!</p>
            <p className="text-yellow-700">
              This module is currently under development. Check back soon for exciting new features!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}