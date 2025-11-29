import type { FC } from 'react'

type Org = {
  id: number
  name: string
  timezone: string | null
}

type Schedule = {
  id: number
  range_start: string
  range_end: string
  status: string
}

type HeroProps = {
  org: Org | null
  schedules: Schedule[]
  loading: boolean
  error: string | null
}

const Hero: FC<HeroProps> = ({ org, schedules, loading, error }) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Yfirlit</h1>
          <p className="text-sm text-slate-300">
            Velkominn í VaktaPlan{org ? ` fyrir ${org.name}` : ''}.
          </p>
        </div>

        {/* placeholder for future user avatar / menu */}
        <div className="h-9 w-9 rounded-full border border-white/30 bg-white/10" />
      </header>

      {error && (
        <p className="text-sm text-red-400 whitespace-pre-wrap mb-4">
          {error}
        </p>
      )}

      {!loading && !error && (
        <main className="grid gap-4 md:grid-cols-3">
          <section className="rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
              Vinnustaður
            </p>
            <p className="text-lg font-medium">
              {org ? org.name : 'Ekki fundinn'}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Tímabelti: {org?.timezone ?? '—'}
            </p>
          </section>

          <section className="rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
              Vaktaplön
            </p>
            <p className="text-lg font-medium">{schedules.length}</p>
            <p className="text-xs text-slate-400 mt-1">
              Heildarfjöldi plana í kerfinu.
            </p>
          </section>

          <section className="rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
              Síðasta plan
            </p>
            {schedules.length === 0 ? (
              <p className="text-sm text-slate-300">Engin plön ennþá.</p>
            ) : (
              <p className="text-sm text-slate-100">
                {schedules[schedules.length - 1].range_start} –{' '}
                {schedules[schedules.length - 1].range_end}
              </p>
            )}
          </section>
        </main>
      )}
    </div>
  )
}

export default Hero
