begin;

create table if not exists public.pmp_discord_members (
    guild_id text not null,
    user_id text not null,
    synced_at timestamptz not null,
    primary key (guild_id, user_id)
);

create table if not exists public.pmp_discord_member_roles (
    guild_id text not null,
    user_id text not null,
    role_id text not null,
    role_name text not null,
    primary key (guild_id, user_id, role_id),
    foreign key (guild_id, user_id) references public.pmp_discord_members on delete cascade
);

create index if not exists pmp_discord_member_roles_by_role
    on public.pmp_discord_member_roles (guild_id, role_id);

alter table public.pmp_discord_members enable row level security;
alter table public.pmp_discord_member_roles enable row level security;
revoke all on table public.pmp_discord_members, public.pmp_discord_member_roles
    from public, anon, authenticated;
grant select, insert, update, delete on table public.pmp_discord_members to service_role;
grant select, insert, delete on table public.pmp_discord_member_roles to service_role;

create or replace function public.sync_pmp_discord_members(p_guild_id text, p_members jsonb)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if p_guild_id is null or p_guild_id !~ '^[0-9]+$'
        or jsonb_typeof(p_members) is distinct from 'array' then
        raise exception 'Expected a guild ID and a member array' using errcode = '22023';
    end if;
    if jsonb_array_length(p_members) = 0 then
        raise exception 'Member snapshot cannot be empty' using errcode = '22023';
    end if;

    -- Serialize snapshot writes for this guild within the transaction.
    perform pg_advisory_xact_lock(hashtextextended('pmp_discord_members:' || p_guild_id, 0));

    insert into public.pmp_discord_members (guild_id, user_id, synced_at)
    select p_guild_id, member.user_id, statement_timestamp()
    from jsonb_to_recordset(p_members) as member(user_id text)
    on conflict (guild_id, user_id) do update
    set synced_at = excluded.synced_at;

    delete from public.pmp_discord_member_roles where guild_id = p_guild_id;

    insert into public.pmp_discord_member_roles (guild_id, user_id, role_id, role_name)
    select p_guild_id, member.user_id, assigned.id, assigned.name
    from jsonb_to_recordset(p_members) as member(user_id text, roles jsonb)
    cross join lateral jsonb_to_recordset(member.roles) as assigned(id text, name text);

    delete from public.pmp_discord_members as stored
    where stored.guild_id = p_guild_id and not exists (
        select 1 from jsonb_to_recordset(p_members) as member(user_id text)
        where member.user_id = stored.user_id
    );
end;
$$;

revoke all on function public.sync_pmp_discord_members(text, jsonb) from public, anon, authenticated;
grant execute on function public.sync_pmp_discord_members(text, jsonb) to service_role;

commit;
