import axios from 'axios';
import type {
    InvestigationReportResponse,
    InvestigationListItem,
    IncidentPayload,
} from '../types';

const api = axios.create({
    baseURL: '/api/v1',
    headers: { 'Content-Type': 'application/json' },
    timeout: 120_000, // 2 min for heavy analysis
});

export const investigationsApi = {
    /** Submit a new incident investigation */
    analyze: (payload: IncidentPayload): Promise<InvestigationReportResponse> =>
        api.post<InvestigationReportResponse>('/investigations/analyze', payload)
            .then((r) => r.data),

    /** List all past investigations */
    list: (): Promise<InvestigationListItem[]> =>
        api.get<InvestigationListItem[]>('/investigations').then((r) => r.data),

    /** Get a specific investigation by ID */
    get: (id: string): Promise<InvestigationReportResponse> =>
        api.get<InvestigationReportResponse>(`/investigations/${id}`).then((r) => r.data),
};
