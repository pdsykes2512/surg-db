interface EpisodeDetailModalProps {
  episode: any
  onClose: () => void
  onEdit: () => void
}

export function EpisodeDetailModal({ episode, onClose, onEdit }: EpisodeDetailModalProps) {
  if (!episode) return null

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style={{ margin: 0 }}>
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Episode Details</h2>
            <p className="text-sm text-gray-500 mt-1">{episode.surgery_id}</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onEdit}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Edit
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Patient ID</label>
                <p className="text-sm text-gray-900 mt-1">{episode.patient_id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Surgery Date</label>
                <p className="text-sm text-gray-900 mt-1">
                  {formatDate(episode.perioperative_timeline.surgery_date)}
                </p>
              </div>
            </div>
          </div>

          {/* Classification */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Classification</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Urgency</label>
                <p className="text-sm text-gray-900 mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    episode.classification.urgency === 'emergency' ? 'bg-red-100 text-red-800' :
                    episode.classification.urgency === 'urgent' ? 'bg-orange-100 text-orange-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {episode.classification.urgency}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Complexity</label>
                <p className="text-sm text-gray-900 mt-1 capitalize">
                  {episode.classification.complexity || '—'}
                </p>
              </div>
              <div className="md:col-span-3">
                <label className="text-sm font-medium text-gray-500">Primary Diagnosis</label>
                <p className="text-sm text-gray-900 mt-1">{episode.classification.primary_diagnosis}</p>
              </div>
              {episode.classification.indication && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Indication</label>
                  <p className="text-sm text-gray-900 mt-1 capitalize">{episode.classification.indication}</p>
                </div>
              )}
            </div>
          </div>

          {/* Procedure */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Procedure</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-gray-500">Primary Procedure</label>
                <p className="text-sm text-gray-900 mt-1">{episode.procedure.primary_procedure}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Approach</label>
                <p className="text-sm text-gray-900 mt-1 capitalize">{episode.procedure.approach}</p>
              </div>
              {episode.procedure.additional_procedures?.length > 0 && (
                <div className="md:col-span-2">
                  <label className="text-sm font-medium text-gray-500">Additional Procedures</label>
                  <p className="text-sm text-gray-900 mt-1">
                    {episode.procedure.additional_procedures.join(', ')}
                  </p>
                </div>
              )}
              {episode.procedure.description && (
                <div className="md:col-span-2">
                  <label className="text-sm font-medium text-gray-500">Description</label>
                  <p className="text-sm text-gray-900 mt-1">{episode.procedure.description}</p>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Perioperative Timeline</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Admission Date</label>
                <p className="text-sm text-gray-900 mt-1">
                  {formatDate(episode.perioperative_timeline.admission_date)}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Surgery Date</label>
                <p className="text-sm text-gray-900 mt-1">
                  {formatDate(episode.perioperative_timeline.surgery_date)}
                </p>
              </div>
              {episode.perioperative_timeline.operation_duration_minutes && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Operation Duration</label>
                  <p className="text-sm text-gray-900 mt-1">
                    {episode.perioperative_timeline.operation_duration_minutes} minutes
                  </p>
                </div>
              )}
              {episode.perioperative_timeline.discharge_date && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Discharge Date</label>
                  <p className="text-sm text-gray-900 mt-1">
                    {formatDate(episode.perioperative_timeline.discharge_date)}
                  </p>
                </div>
              )}
              {episode.perioperative_timeline.length_of_stay_days && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Length of Stay</label>
                  <p className="text-sm text-gray-900 mt-1">
                    {episode.perioperative_timeline.length_of_stay_days} days
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Surgical Team */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Surgical Team</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Primary Surgeon</label>
                <p className="text-sm text-gray-900 mt-1">{episode.team.primary_surgeon}</p>
              </div>
              {episode.team.assistant_surgeons?.length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Assistant Surgeons</label>
                  <p className="text-sm text-gray-900 mt-1">
                    {episode.team.assistant_surgeons.join(', ')}
                  </p>
                </div>
              )}
              {episode.team.anesthesiologist && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Anesthesiologist</label>
                  <p className="text-sm text-gray-900 mt-1">{episode.team.anesthesiologist}</p>
                </div>
              )}
            </div>
          </div>

          {/* Intraoperative Details */}
          {episode.intraoperative && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Intraoperative Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {episode.intraoperative.anesthesia_type && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Anesthesia Type</label>
                    <p className="text-sm text-gray-900 mt-1 capitalize">
                      {episode.intraoperative.anesthesia_type}
                    </p>
                  </div>
                )}
                {episode.intraoperative.blood_loss_ml !== null && episode.intraoperative.blood_loss_ml !== undefined && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Blood Loss</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.intraoperative.blood_loss_ml} mL</p>
                  </div>
                )}
                {episode.intraoperative.transfusion_required && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Transfusion</label>
                    <p className="text-sm text-gray-900 mt-1">
                      {episode.intraoperative.units_transfused || 0} units
                    </p>
                  </div>
                )}
                {episode.intraoperative.findings && (
                  <div className="md:col-span-3">
                    <label className="text-sm font-medium text-gray-500">Operative Findings</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.intraoperative.findings}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Audit Trail */}
          {episode.audit_trail && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Audit Trail</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <label className="text-sm font-medium text-gray-500">Created By</label>
                  <p className="text-sm text-gray-900 mt-1">{episode.audit_trail.created_by}</p>
                  <p className="text-xs text-gray-500">
                    {formatDate(episode.audit_trail.created_at)}
                  </p>
                </div>
                {episode.audit_trail.updated_by && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Last Updated By</label>
                    <p className="text-sm text-gray-900 mt-1">{episode.audit_trail.updated_by}</p>
                    <p className="text-xs text-gray-500">
                      {formatDate(episode.audit_trail.updated_at)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
