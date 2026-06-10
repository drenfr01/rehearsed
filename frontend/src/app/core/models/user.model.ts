// Types are generated from the backend OpenAPI spec via HeyAPI (npm run generate:api).
import type { UpdateUserApiV1AdminUsersUserIdPutData } from '../api';

export type { UserResponse as User, UserCreateWritable as UserCreate } from '../api';

// The admin user update endpoint takes its fields as query parameters,
// so the update payload type comes from the generated operation data.
export type UserUpdate = NonNullable<UpdateUserApiV1AdminUsersUserIdPutData['query']>;
