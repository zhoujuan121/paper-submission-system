# generate_password_hash.py - 密码哈希生成工具
import hashlib


def hash_password(password):
    """生成密码的SHA256哈希值"""
    return hashlib.sha256(password.encode()).hexdigest()


if __name__ == "__main__":
    print("🔐 密码哈希生成工具")
    print("=" * 50)

    while True:
        password = input("\n请输入要哈希的密码（输入q退出）: ")
        if password.lower() == 'q':
            break

        if password:
            hashed = hash_password(password)
            print(f"📝 明文密码: {password}")
            print(f"🔒 哈希值: {hashed}")
            print(f"⚙️ Secrets配置:")
            print(f'admin_password_hash = "{hashed}"')
            print("-" * 50)