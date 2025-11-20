'use client';

import { Building2, ExternalLink, Globe2, Mail, MapPin, Phone, FileText } from 'lucide-react';
import { useCompanyDetail } from '@/lib/queries';
import Address from '@/components/address';
import IndustryCodes from '@/components/industry-codes';
import PersonList from '@/components/person-list';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Event } from '@/lib/schemas';

export default function CompanyPage({ params }: { params: { source_id: string } }) {
  const { data, isLoading } = useCompanyDetail(params.source_id);

  if (isLoading) {
    return <DetailSkeleton />;
  }
  if (!data) return <div>Not found</div>;

  const { company, events, persons, industry_codes } = data;

  return (
    <div className="space-y-6">
      <Card className="shadow-sm">
        <CardHeader className="gap-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Building2 className="h-5 w-5" />
                <span className="text-sm">Unternehmensprofil</span>
              </div>
              <CardTitle className="text-3xl leading-tight">{company.name}</CardTitle>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {(company.city || company.country || company.postal_code) && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {[company.postal_code, company.city, company.country].filter(Boolean).join(' ')}
                  </span>
                )}
                {company.website && (
                  <a
                    href={company.website.startsWith('http') ? company.website : `https://${company.website}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                  >
                    <Globe2 className="h-4 w-4" />
                    {company.website.replace(/^https?:\/\//, '')}
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {renderStatusBadge(company.status, company.terminated)}
              {company.legal_form && <Badge variant="secondary">{company.legal_form}</Badge>}
              {company.register_id && <Badge variant="outline">HR: {company.register_id}</Badge>}
            </div>
          </div>
        </CardHeader>
      </Card>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile">Stammdaten</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="persons">Personen</TabsTrigger>
          <TabsTrigger value="relations">Beziehungen</TabsTrigger>
          <TabsTrigger value="raw">Rohdaten</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Adresse</CardTitle>
                <CardDescription>Hauptsitz und regionale Einordnung.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <Address company={company} />
                {company.state && <div className="text-muted-foreground">Bundesland: {company.state}</div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Kontakt</CardTitle>
                <CardDescription>Kommunikationswege zum Unternehmen.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {company.email ? (
                  <a href={`mailto:${company.email}`} className="flex items-center gap-2 text-blue-600 hover:underline">
                    <Mail className="h-4 w-4" />
                    {company.email}
                  </a>
                ) : (
                  <div className="text-muted-foreground">Keine E-Mail hinterlegt.</div>
                )}
                {company.phone ? (
                  <a href={`tel:${company.phone}`} className="flex items-center gap-2 text-blue-600 hover:underline">
                    <Phone className="h-4 w-4" />
                    {company.phone}
                  </a>
                ) : (
                  <div className="text-muted-foreground">Keine Telefonnummer hinterlegt.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Handelsregister</CardTitle>
                <CardDescription>Offizielle Registerdaten.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {company.register_id ? (
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    <span>{company.register_id}</span>
                  </div>
                ) : (
                  <div className="text-muted-foreground">Kein Registereintrag angegeben.</div>
                )}
                {company.register_city && <div>Registergericht: {company.register_city}</div>}
                {company.register_country && <div>Registerland: {company.register_country}</div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Branchen</CardTitle>
                <CardDescription>WZ-Codes und Tätigkeitsfelder.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {industry_codes && industry_codes.length > 0 ? (
                  <IndustryCodes codes={industry_codes} />
                ) : (
                  <div className="text-muted-foreground">Keine Branchen hinterlegt.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="events">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Events</CardTitle>
              <CardDescription>Wichtige Änderungen und Meldungen.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {events && events.length > 0 ? (
                <div className="space-y-3">
                  {events.map((event, idx) => (
                    <EventRow key={event.event_id ?? idx} event={event} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Keine Events verfügbar.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="persons">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Personen & Rollen</CardTitle>
              <CardDescription>Geschäftsführer, Prokura und weitere Mandate.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {persons && persons.length > 0 ? <PersonList persons={persons} /> : (
                <p className="text-sm text-muted-foreground">Keine Personen hinterlegt.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="relations">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Beziehungen</CardTitle>
              <CardDescription>Verknüpfte Unternehmen und Konzernstruktur.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Noch keine Beziehungen erfasst.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="raw">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Rohdaten</CardTitle>
              <CardDescription>JSON-Ansicht des Datensatzes.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded-md bg-muted p-4 text-xs">
                {JSON.stringify(data, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function renderStatusBadge(status?: string | null, terminated?: boolean | null) {
  if (terminated) {
    return <Badge variant="destructive">Liquidiert</Badge>;
  }
  if (!status) return <Badge variant="muted">Status unbekannt</Badge>;
  const normalized = status.trim().toLowerCase();
  if (normalized === 'active' || normalized === 'aktiv') return <Badge variant="success">Aktiv</Badge>;
  if (normalized === 'processing') return <Badge variant="warning">In Bearbeitung</Badge>;
  return <Badge variant="outline" className="capitalize">{status}</Badge>;
}

function EventRow({ event }: { event: Event }) {
  return (
    <div className="flex gap-3 rounded-md border border-muted px-3 py-2">
      <div className="w-28 text-sm font-medium text-muted-foreground">{event.event_date ?? '–'}</div>
      <div className="flex-1 space-y-1">
        <Badge variant="secondary" className="capitalize">
          {event.event_type ?? 'Event'}
        </Badge>
        {event.description && (
          <p className="text-sm text-foreground/90 overflow-hidden text-ellipsis">{event.description}</p>
        )}
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-64" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-20" />
          </div>
        </CardHeader>
      </Card>
      <Card>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {[...Array(4)].map((_, idx) => (
            <div key={idx} className="space-y-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-16 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
