import { capitalize, formatAnatomicalSite, formatClinicalTNM, formatPathologicalTNM } from '../../utils/formatters'
import { calculateStage, formatStage } from '../../utils/cancerStaging'
import { Button } from '../common/Button'

interface TumourSummaryModalProps {
  tumour: any
  onClose: () => void
  onEdit: () => void
}

export function TumourSummaryModal({ tumour, onClose, onEdit }: TumourSummaryModalProps) {
  if (!tumour) return null

  const getTumourTypeColor = (type: string) => {
    switch (type) {
      case 'primary': return 'bg-blue-100 text-blue-800'
      case 'metastasis': return 'bg-red-100 text-red-800'
      case 'recurrence': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStageColor = (stage: string) => {
    if (!stage || stage === 'Unknown') return 'bg-gray-100 text-gray-800'
    if (stage.includes('0') || stage.includes('I')) return 'bg-green-100 text-green-800'
    if (stage.includes('II')) return 'bg-yellow-100 text-yellow-800'
    if (stage.includes('III')) return 'bg-orange-100 text-orange-800'
    if (stage.includes('IV')) return 'bg-red-100 text-red-800'
    return 'bg-gray-100 text-gray-800'
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
      <div className="grid grid-cols-3 gap-4 py-2">
        <dt className="text-sm font-medium text-gray-500">{label}</dt>
        <dd className="text-sm text-gray-900 col-span-2">{value}</dd>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg shadow-xl max-w-full sm:max-w-2xl md:max-w-3xl lg:max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 sm:px-6 py-3 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Tumour Summary</h2>
            <p className="text-blue-100 text-sm mt-1">{tumour.tumour_id}</p>
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
              label="Tumour Type" 
              value={
                <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getTumourTypeColor(tumour.tumour_type)}`}>
                  {capitalize(tumour.tumour_type)}
                </span>
              }
            />
            <Field 
              label="Site" 
              value={formatAnatomicalSite(tumour.site)}
            />
            <Field label="ICD-10 Code" value={tumour.icd10_code} />
            <Field label="SNOMED Morphology" value={tumour.snomed_morphology} />
            {tumour.tumour_type === 'primary' && (
              <Field label="Distance from Anal Verge" value={tumour.distance_from_anal_verge ? `${tumour.distance_from_anal_verge} cm` : undefined} />
            )}
            <Field label="Diagnosis Date" value={tumour.diagnosis_date} />
          </Section>

          {/* Clinical Staging (TNM) */}
          <Section title="Clinical Staging">
            <Field label="TNM Version" value={tumour.tnm_version ? `Version ${tumour.tnm_version}` : undefined} />
            {(tumour.clinical_t || tumour.clinical_n || tumour.clinical_m) && (
              <div className="grid grid-cols-3 gap-4 py-2">
                <dt className="text-sm font-medium text-gray-500">TNM (cTNM)</dt>
                <dd className="text-sm text-gray-900 col-span-2">
                  <span className="font-mono">
                    {formatClinicalTNM(tumour.clinical_t, tumour.clinical_n, tumour.clinical_m)}
                  </span>
                </dd>
              </div>
            )}
            {tumour.clinical_stage && (
              <Field 
                label="Clinical Stage" 
                value={
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStageColor(tumour.clinical_stage)}`}>
                    {tumour.clinical_stage}
                  </span>
                }
              />
            )}
          </Section>

          {/* Pathological Staging (TNM) */}
          <Section title="Pathological Staging">
            {(tumour.pathological_t || tumour.pathological_n || tumour.pathological_m) && (() => {
              const calculatedStage = calculateStage('bowel', tumour.pathological_t, tumour.pathological_n, tumour.pathological_m)
              return (
                <>
                  <div className="grid grid-cols-3 gap-4 py-2">
                    <dt className="text-sm font-medium text-gray-500">TNM (pTNM)</dt>
                    <dd className="text-sm text-gray-900 col-span-2">
                      <span className="font-mono">
                        {formatPathologicalTNM(tumour.pathological_t, tumour.pathological_n, tumour.pathological_m)}
                      </span>
                    </dd>
                  </div>
                  {calculatedStage !== 'Unknown' && (
                    <div className="grid grid-cols-3 gap-4 py-2">
                      <dt className="text-sm font-medium text-gray-500">Pathological Stage</dt>
                      <dd className="text-sm text-gray-900 col-span-2">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStageColor(calculatedStage)}`}>
                          {formatStage(calculatedStage)}
                        </span>
                      </dd>
                    </div>
                  )}
                </>
              )
            })()}
          </Section>

          {/* Histopathology */}
          {(tumour.histology_type || tumour.grade || tumour.lymphovascular_invasion !== undefined || 
            tumour.perineural_invasion !== undefined || tumour.tumour_perforation !== undefined) && (
            <Section title="Histopathology">
              <Field label="Histology Type" value={tumour.histology_type?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
              <Field label="Grade" value={tumour.grade?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())} />
              {(tumour.lymphovascular_invasion !== undefined || tumour.perineural_invasion !== undefined) && (
                <div className="grid grid-cols-3 gap-4 py-2">
                  <dt className="text-sm font-medium text-gray-500">Invasion</dt>
                  <dd className="text-sm text-gray-900 col-span-2">
                    {tumour.lymphovascular_invasion !== undefined && (
                      <span className="mr-3">LVI: {tumour.lymphovascular_invasion ? 'Present' : 'Absent'}</span>
                    )}
                    {tumour.perineural_invasion !== undefined && (
                      <span>PNI: {tumour.perineural_invasion ? 'Present' : 'Absent'}</span>
                    )}
                  </dd>
                </div>
              )}
              <Field label="Tumour Perforation" value={tumour.tumour_perforation !== undefined ? (tumour.tumour_perforation ? 'Yes' : 'No') : undefined} />
            </Section>
          )}

          {/* Lymph Nodes */}
          {(tumour.lymph_nodes_examined !== undefined || tumour.lymph_nodes_positive !== undefined) && (
            <Section title="Lymph Nodes">
              <div className="grid grid-cols-3 gap-4 py-2">
                <dt className="text-sm font-medium text-gray-500">Nodes</dt>
                <dd className="text-sm text-gray-900 col-span-2">
                  {tumour.lymph_nodes_positive !== undefined && tumour.lymph_nodes_examined !== undefined ? (
                    <span>
                      <span className="font-semibold">{tumour.lymph_nodes_positive}/{tumour.lymph_nodes_examined}</span>
                      <span className="text-gray-500 ml-2">({((tumour.lymph_nodes_positive / tumour.lymph_nodes_examined) * 100).toFixed(1)}% positive)</span>
                    </span>
                  ) : (
                    <span>
                      {tumour.lymph_nodes_examined !== undefined && `${tumour.lymph_nodes_examined} examined`}
                      {tumour.lymph_nodes_positive !== undefined && `${tumour.lymph_nodes_positive} positive`}
                    </span>
                  )}
                </dd>
              </div>
            </Section>
          )}

          {/* Margins */}
          {(tumour.crm_status || tumour.crm_distance_mm !== undefined || tumour.distal_margin_mm !== undefined || tumour.proximal_margin_mm !== undefined) && (
            <Section title="Resection Margins">
              {tumour.crm_status && (
                <Field 
                  label="CRM Status" 
                  value={
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                      tumour.crm_status === 'clear' ? 'bg-green-100 text-green-800' :
                      tumour.crm_status === 'involved' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {tumour.crm_status.replace('_', ' ').toUpperCase()}
                    </span>
                  }
                />
              )}
              <div className="grid grid-cols-3 gap-4 py-2">
                <dt className="text-sm font-medium text-gray-500">Margins (mm)</dt>
                <dd className="text-sm text-gray-900 col-span-2">
                  {tumour.crm_distance_mm !== undefined && (
                    <span className="mr-3">CRM: {tumour.crm_distance_mm}</span>
                  )}
                  {tumour.proximal_margin_mm !== undefined && (
                    <span className="mr-3">Proximal: {tumour.proximal_margin_mm}</span>
                  )}
                  {tumour.distal_margin_mm !== undefined && (
                    <span>Distal: {tumour.distal_margin_mm}</span>
                  )}
                </dd>
              </div>
            </Section>
          )}

          {/* Molecular/Genetic */}
          {(tumour.msi_status || tumour.kras_status || tumour.nras_status || tumour.braf_status) && (
            <Section title="Molecular Markers">
              <div className="grid grid-cols-3 gap-4 py-2">
                <dt className="text-sm font-medium text-gray-500">Biomarkers</dt>
                <dd className="text-sm text-gray-900 col-span-2">
                  {tumour.msi_status && (
                    <span className="mr-3">MSI: <span className="font-semibold">{tumour.msi_status.toUpperCase()}</span></span>
                  )}
                  {tumour.kras_status && (
                    <span className="mr-3">KRAS: <span className="font-semibold">{tumour.kras_status.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</span></span>
                  )}
                  {tumour.nras_status && (
                    <span className="mr-3">NRAS: <span className="font-semibold">{tumour.nras_status.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</span></span>
                  )}
                  {tumour.braf_status && (
                    <span>BRAF: <span className="font-semibold">{tumour.braf_status.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</span></span>
                  )}
                </dd>
              </div>
            </Section>
          )}

          {/* Additional Information */}
          {tumour.notes && (
            <Section title="Additional Notes">
              <div className="text-sm text-gray-900 whitespace-pre-wrap">{tumour.notes}</div>
            </Section>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 flex justify-between">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button variant="primary" onClick={onEdit}>
            Edit Tumour
          </Button>
        </div>
      </div>
    </div>
  )
}
