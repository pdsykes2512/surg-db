import { formatDate, formatTreatmentType, formatSurgeon, formatAnatomicalSite } from '../utils/formatters'
import { formatTrustName } from '../utils/nhsTrusts'
import { Button } from './Button'

interface TreatmentSummaryModalProps {
  treatment: any
  onClose: () => void
  onEdit: () => void
}

export function TreatmentSummaryModal({ treatment, onClose, onEdit }: TreatmentSummaryModalProps) {
  if (!treatment) return null

  const getTreatmentTypeColor = (type: string) => {
    switch (type) {
      case 'surgery': return 'bg-blue-100 text-blue-800'
      case 'chemotherapy': return 'bg-purple-100 text-purple-800'
      case 'radiotherapy': return 'bg-green-100 text-green-800'
      case 'immunotherapy': return 'bg-yellow-100 text-yellow-800'
      case 'targeted_therapy': return 'bg-pink-100 text-pink-800'
      case 'other': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const Section = ({ title, children }: { title: string, children: React.ReactNode }) => (
    <div className="mb-4">
      <h3 className="text-base font-semibold text-gray-900 mb-2 pb-1 border-b border-gray-200">{title}</h3>
      <div className="space-y-0">
        {children}
      </div>
    </div>
  )

  const Field = ({ label, value }: { label: string, value: any }) => {
    if (!value && value !== 0 && value !== false) return null
    return (
      <div className="grid grid-cols-3 gap-4 py-1.5 border-b border-gray-100 last:border-0">
        <dt className="text-xs font-medium text-gray-500">{label}</dt>
        <dd className="text-sm text-gray-900 col-span-2">{value}</dd>
      </div>
    )
  }

  const CompactField = ({ label, value }: { label: string, value: any }) => {
    if (!value && value !== 0 && value !== false) return null
    return (
      <div className="flex items-center gap-2">
        <dt className="text-xs font-medium text-gray-500 whitespace-nowrap">{label}:</dt>
        <dd className="text-sm text-gray-900">{value}</dd>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-3 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Treatment Summary</h2>
            <p className="text-purple-100 text-sm mt-1">{treatment.treatment_id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Basic Information */}
          <Section title="Basic Information">
            <Field 
              label="Treatment Type" 
              value={
                <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getTreatmentTypeColor(treatment.treatment_type)}`}>
                  {formatTreatmentType(treatment.treatment_type)}
                </span>
              }
            />
            <Field label="Treatment Date" value={formatDate(treatment.treatment_date)} />
            <Field label="Surgeon/Oncologist" value={formatSurgeon(treatment.surgeon || treatment.oncologist)} />
            <Field label="Provider Organisation" value={formatTrustName(treatment.provider_organisation)} />
            <Field label="Institution" value={treatment.institution} />
          </Section>

          {/* Surgery Specific */}
          {treatment.treatment_type === 'surgery' && (
            <>
              <Section title="Surgical Details">
                <Field label="Procedure Name" value={treatment.procedure_name} />
                <Field label="OPCS-4 Code" value={treatment.opcs4_code} />
                <div className="grid grid-cols-3 gap-4 py-1.5 border-b border-gray-100">
                  <CompactField label="Approach" value={treatment.approach?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
                  <CompactField label="Urgency" value={treatment.urgency?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
                  <CompactField label="Complexity" value={treatment.complexity?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
                </div>
                <div className="grid grid-cols-2 gap-4 py-1.5 border-b border-gray-100">
                  <CompactField label="ASA Score" value={treatment.asa_score ? `ASA ${treatment.asa_score}` : undefined} />
                  <CompactField label="Anesthesia" value={treatment.anesthesia_type?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
                </div>
              </Section>

              <Section title="Surgical Team">
                <Field label="Primary Surgeon" value={formatSurgeon(treatment.surgeon)} />
                <Field label="Assistant Surgeon" value={treatment.assistant_surgeon} />
                <Field label="Assistant Grade" value={treatment.assistant_grade} />
                <Field label="Second Assistant" value={treatment.second_assistant} />
                <Field label="Surgical Fellow" value={treatment.surgical_fellow ? 'Yes' : treatment.surgical_fellow === false ? 'No' : undefined} />
                {treatment.assistant_surgeons?.length > 0 && (
                  <Field label="Assistant Surgeons" value={treatment.assistant_surgeons.join(', ')} />
                )}
                <Field label="Anaesthetist" value={treatment.anaesthetist} />
              </Section>

              <Section title="Timeline & Duration">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <CompactField label="Admission" value={formatDate(treatment.admission_date)} />
                    <CompactField label="Surgery" value={formatDate(treatment.treatment_date)} />
                    <CompactField label="Discharge" value={formatDate(treatment.discharge_date)} />
                  </div>
                  <div className="space-y-1.5">
                    <CompactField label="Operation Duration" value={treatment.operation_duration_minutes ? `${treatment.operation_duration_minutes} min` : undefined} />
                    <CompactField label="Anaesthesia Duration" value={treatment.anesthesia_duration_minutes ? `${treatment.anesthesia_duration_minutes} min` : undefined} />
                    <CompactField label="Length of Stay" value={treatment.length_of_stay ? `${treatment.length_of_stay} days` : undefined} />
                  </div>
                </div>
              </Section>

              <Section title="Intraoperative Details">
                <div className="grid grid-cols-2 gap-4 py-1.5 border-b border-gray-100">
                  <CompactField label="Blood Loss" value={treatment.blood_loss_ml ? `${treatment.blood_loss_ml} ml` : undefined} />
                  <CompactField label="Transfusion" value={treatment.transfusion_required ? (treatment.units_transfused ? `Yes (${treatment.units_transfused} units)` : 'Yes') : 'No'} />
                </div>
                <div className="grid grid-cols-2 gap-4 py-1.5 border-b border-gray-100">
                  <CompactField label="Drains" value={treatment.drains_placed ? (treatment.drain_types?.length > 0 ? `Yes (${treatment.drain_types.join(', ')})` : 'Yes') : 'No'} />
                </div>
                {(treatment.approach === 'converted_to_open' || treatment.laparoscopic_converted) && treatment.conversion_reason && (
                  <Field label="Conversion Reason" value={
                    <span className="text-gray-900">{treatment.conversion_reason.charAt(0).toUpperCase() + treatment.conversion_reason.slice(1).replace(/_/g, ' ')}</span>
                  } />
                )}
                {treatment.specimens_sent?.length > 0 && (
                  <Field label="Specimens Sent" value={treatment.specimens_sent.join(', ')} />
                )}
                {treatment.findings && (
                  <Field label="Operative Findings" value={treatment.findings} />
                )}
              </Section>

              {/* Colorectal-Specific Details */}
              {(treatment.stoma_created !== undefined || treatment.anastomosis_performed !== undefined || treatment.surgical_intent) && (
                <Section title="Colorectal-Specific Details">
                  {/* Surgical Intent */}
                  {treatment.surgical_intent && (
                    <Field 
                      label="Surgical Intent" 
                      value={
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                          treatment.surgical_intent === 'curative' ? 'bg-green-100 text-green-800' :
                          treatment.surgical_intent === 'palliative' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {treatment.surgical_intent.charAt(0).toUpperCase() + treatment.surgical_intent.slice(1)}
                        </span>
                      }
                    />
                  )}
                  
                  {/* Stoma Information */}
                  {treatment.stoma_created !== undefined && (
                    <Field 
                      label="Stoma Created" 
                      value={
                        treatment.stoma_created ? (
                          <div className="space-y-1">
                            <div>
                              <span className="font-semibold">Yes</span>
                              {treatment.stoma_type && (
                                <span className="ml-2">
                                  ({treatment.stoma_type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())})
                                </span>
                              )}
                            </div>
                            {treatment.planned_reversal_date && (
                              <div className="text-sm text-gray-600">
                                Planned Reversal: {formatDate(treatment.planned_reversal_date)}
                              </div>
                            )}
                            {treatment.stoma_closure_date && (
                              <div className="text-sm text-gray-600">
                                Actual Closure: {formatDate(treatment.stoma_closure_date)}
                              </div>
                            )}
                          </div>
                        ) : 'No'
                      }
                    />
                  )}
                  
                  {treatment.reverses_stoma_from_treatment_id && (
                    <Field 
                      label="Reversal Surgery" 
                      value={
                        <div className="text-sm">
                          This surgery reverses stoma from treatment: <span className="font-mono">{treatment.reverses_stoma_from_treatment_id}</span>
                        </div>
                      }
                    />
                  )}
                  
                  {/* Anastomosis Information */}
                  {treatment.anastomosis_performed !== undefined && (
                    <Field 
                      label="Anastomosis" 
                      value={
                        treatment.anastomosis_performed ? (
                          <div className="space-y-1">
                            <div><span className="font-semibold">Yes</span></div>
                            {treatment.anastomosis_type && (
                              <div className="text-sm">
                                Type: {treatment.anastomosis_type.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join('-')}
                              </div>
                            )}
                            {treatment.anastomosis_height_cm !== undefined && (
                              <div className="text-sm">
                                Height: {treatment.anastomosis_height_cm} cm from anal verge
                              </div>
                            )}
                            {treatment.anterior_resection_type && (
                              <div className="text-sm">
                                Resection: {treatment.anterior_resection_type.replace(/_/g, ' ').toUpperCase()}
                              </div>
                            )}
                          </div>
                        ) : 'No'
                      }
                    />
                  )}
                </Section>
              )}
            </>
          )}

          {/* Chemotherapy Specific */}
          {treatment.treatment_type === 'chemotherapy' && (
            <Section title="Chemotherapy Details">
              <Field label="Regimen" value={treatment.regimen} />
              <Field label="Intent" value={treatment.intent?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
              <Field label="Cycle Number" value={treatment.cycle_number} />
              <Field label="Total Cycles Planned" value={treatment.total_cycles} />
              <Field label="Dose Reduction" value={treatment.dose_reduction !== undefined ? (treatment.dose_reduction ? 'Yes' : 'No') : undefined} />
              {treatment.dose_reduction && (
                <Field label="Dose Reduction Reason" value={treatment.dose_reduction_reason} />
              )}
            </Section>
          )}

          {/* Radiotherapy Specific */}
          {treatment.treatment_type === 'radiotherapy' && (
            <Section title="Radiotherapy Details">
              <Field label="Site" value={formatAnatomicalSite(treatment.site)} />
              <Field label="Intent" value={treatment.intent?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
              <Field label="Technique" value={treatment.technique?.toUpperCase()} />
              <Field label="Total Dose" value={treatment.total_dose ? `${treatment.total_dose} Gy` : undefined} />
              <Field label="Fractions" value={treatment.fractions} />
              <Field label="Dose Per Fraction" value={treatment.dose_per_fraction ? `${treatment.dose_per_fraction} Gy` : undefined} />
              <Field label="Concurrent Chemotherapy" value={treatment.concurrent_chemo !== undefined ? (treatment.concurrent_chemo ? 'Yes' : 'No') : undefined} />
            </Section>
          )}

          {/* Immunotherapy Specific */}
          {treatment.treatment_type === 'immunotherapy' && (
            <Section title="Immunotherapy Details">
              <Field label="Agent" value={treatment.agent} />
              <Field label="Dose" value={treatment.dose} />
              <Field label="Frequency" value={treatment.frequency} />
            </Section>
          )}

          {/* Targeted Therapy Specific */}
          {treatment.treatment_type === 'targeted_therapy' && (
            <Section title="Targeted Therapy Details">
              <Field label="Agent" value={treatment.agent} />
              <Field label="Target" value={treatment.target} />
              <Field label="Dose" value={treatment.dose} />
              <Field label="Frequency" value={treatment.frequency} />
            </Section>
          )}

          {/* Complications */}
          {(treatment.complications?.length > 0 || treatment.clavien_dindo_grade || treatment.return_to_theatre || treatment.readmission_30d) && (
            <Section title="Complications & Adverse Events">
              <Field 
                label="Clavien-Dindo Grade" 
                value={treatment.clavien_dindo_grade ? (
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    treatment.clavien_dindo_grade === 'V' ? 'bg-red-100 text-red-800' :
                    treatment.clavien_dindo_grade.startsWith('IV') ? 'bg-orange-100 text-orange-800' :
                    treatment.clavien_dindo_grade.startsWith('III') ? 'bg-yellow-100 text-yellow-800' :
                    treatment.clavien_dindo_grade === 'II' ? 'bg-blue-100 text-blue-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    Grade {treatment.clavien_dindo_grade}
                  </span>
                ) : undefined}
              />
              <Field 
                label="Return to Theatre" 
                value={treatment.return_to_theatre ? (
                  <div>
                    <span className="text-red-600 font-semibold">Yes</span>
                    {treatment.return_to_theatre_reason && (
                      <span className="ml-2 text-gray-600">— {treatment.return_to_theatre_reason}</span>
                    )}
                  </div>
                ) : treatment.return_to_theatre === false ? 'No' : undefined}
              />
              <Field 
                label="30-Day Readmission" 
                value={treatment.readmission_30d ? (
                  <div>
                    <span className="text-orange-600 font-semibold">Yes</span>
                    {treatment.readmission_reason && (
                      <span className="ml-2 text-gray-600">— {treatment.readmission_reason}</span>
                    )}
                  </div>
                ) : treatment.readmission_30d === false ? 'No' : undefined}
              />
              {treatment.complications?.length > 0 && (
                <Field 
                  label="Other Complications" 
                  value={
                    <ul className="list-disc list-inside">
                      {treatment.complications.map((comp: string, idx: number) => (
                        <li key={idx}>{comp}</li>
                      ))}
                    </ul>
                  }
                />
              )}
            </Section>
          )}

          {/* Outcomes */}
          {(treatment.length_of_stay !== undefined || treatment.mortality_30d !== undefined || treatment.mortality_90d !== undefined || treatment.days_to_death !== undefined) && (
            <Section title="Outcomes">
              <Field label="Length of Stay" value={treatment.length_of_stay ? `${treatment.length_of_stay} days` : undefined} />
              
              {treatment.days_to_death !== undefined && treatment.days_to_death !== null && (
                <Field 
                  label="Mortality" 
                  value={
                    <div className="space-y-1">
                      <div className="text-red-600 font-semibold">
                        Deceased {treatment.days_to_death} days after treatment
                      </div>
                      <div className="text-sm text-gray-600">
                        30-day mortality: <span className={treatment.mortality_30d ? "text-red-600 font-semibold" : ""}>{treatment.mortality_30d ? 'Yes' : 'No'}</span>
                        {' • '}
                        90-day mortality: <span className={treatment.mortality_90d ? "text-red-600 font-semibold" : ""}>{treatment.mortality_90d ? 'Yes' : 'No'}</span>
                        {treatment.mortality_1year !== undefined && (
                          <>
                            {' • '}
                            1-year mortality: <span className={treatment.mortality_1year ? "text-red-600 font-semibold" : ""}>{treatment.mortality_1year ? 'Yes' : 'No'}</span>
                          </>
                        )}
                      </div>
                    </div>
                  }
                />
              )}
              
              {treatment.days_to_death === null && treatment.mortality_30d !== undefined && (
                <>
                  <Field label="30-Day Mortality" value={treatment.mortality_30d !== undefined ? (treatment.mortality_30d ? 'Yes' : 'No') : undefined} />
                  <Field label="90-Day Mortality" value={treatment.mortality_90d !== undefined ? (treatment.mortality_90d ? 'Yes' : 'No') : undefined} />
                </>
              )}
            </Section>
          )}

          {/* Response (for systemic therapies) */}
          {treatment.response && (
            <Section title="Treatment Response">
              <Field label="Response" value={treatment.response?.toUpperCase()} />
              <Field label="Response Date" value={treatment.response_date} />
            </Section>
          )}

          {/* Additional Notes */}
          {treatment.notes && (
            <Section title="Additional Notes">
              <div className="text-sm text-gray-900 whitespace-pre-wrap">{treatment.notes}</div>
            </Section>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-between">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button onClick={onEdit}>
            Edit Treatment
          </Button>
        </div>
      </div>
    </div>
  )
}
